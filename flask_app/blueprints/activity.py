from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from typing import List, Tuple, Dict, Any

import numpy as np
import plotly.graph_objects as go
import plotly.offline as pyo
from cachetools import TTLCache, cached
from flask import Blueprint, request, render_template, Response

from flask_app.kalman_filter import create_kalman_filter
from flask_app.shared import call_strava_api, meters_to_feet
from flask_app.gpx_export import create_gpx, gpx_to_string
from flask_app import config


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in meters using Haversine formula."""
    R = 6371000  # Earth's radius in meters

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def calculate_track_distance(coordinates: List[Tuple[float, float]]) -> float:
    """Calculate total distance of a track in meters."""
    total = 0.0
    for i in range(1, len(coordinates)):
        lat1, lon1 = coordinates[i - 1]
        lat2, lon2 = coordinates[i]
        total += haversine_distance(lat1, lon1, lat2, lon2)
    return total


PREFIX = "activity"
bp = Blueprint("activity", __name__, url_prefix=f"/{PREFIX}")

activity_info_cache = TTLCache(maxsize=100, ttl=60 * 60 * 24)  # 24 hours
stream_cache = TTLCache(maxsize=100, ttl=60 * 60 * 24)  # 24 hours


def get_kf_params_from_request() -> Dict[str, Any]:
    """Extract Kalman filter params from request args with defaults."""
    return {
        "uncertainty_pos": float(request.args.get("uncertainty_pos", config.DEFAULT_UNCERTAINTY_POS)),
        "uncertainty_velo": float(request.args.get("uncertainty_velo", config.DEFAULT_UNCERTAINTY_VELO)),
        "process_uncertainty": float(request.args.get("process_uncertainty", config.DEFAULT_PROCESS_UNCERTAINTY)),
        "state_uncertainty": float(request.args.get("state_uncertainty", config.DEFAULT_STATE_UNCERTAINTY)),
    }


def run_kalman_filter(streams: dict, kf_params: Dict[str, Any]) -> List[Tuple[float, float]]:
    """Run Kalman filter on GPS streams and return smoothed predictions."""
    lat = [x[0] for x in streams["latlng"]["data"]]
    long = [x[1] for x in streams["latlng"]["data"]]

    kf = create_kalman_filter(
        lat=lat,
        long=long,
        uncertainty_pos=kf_params["uncertainty_pos"],
        uncertainty_velo=kf_params["uncertainty_velo"],
        state_uncertainty_pos=kf_params["state_uncertainty"],
        q_var=kf_params["process_uncertainty"],
    )
    mu, cov, _, _ = kf.batch_filter(list(zip(lat, long)))
    mu, cov, _, _ = kf.rts_smoother(mu, cov)
    return [(x[0], x[2]) for x in mu]  # [(pred_lat_0, pred_long_0), ...)]


def generate_plot_div(streams: dict, preds: List[Tuple[float, float]]) -> str:
    """Generate Plotly div HTML for the map."""
    fig = get_activity_plot(streams, preds)
    return pyo.plot(fig, output_type="div", include_plotlyjs=False)


@bp.get("/activity_info/<string:activity_id>")
def activity_info(activity_id: str):
    activity_data = get_activity_data(activity_id)
    streams = get_activity_streams(activity_id)
    kf_params = get_kf_params_from_request()
    preds = run_kalman_filter(streams, kf_params)
    plot_div = generate_plot_div(streams, preds)

    # Calculate smoothed distance
    smoothed_distance = calculate_track_distance(preds)

    return render_template(
        "activity.html",
        data=activity_data,
        plot_div=plot_div,
        kf_params=kf_params,
        smoothed_distance=smoothed_distance,
    )


@bp.get("/map/<string:activity_id>")
def activity_map(activity_id: str):
    """Return just the map partial for HTMX updates."""
    activity_data = get_activity_data(activity_id)
    streams = get_activity_streams(activity_id)
    kf_params = get_kf_params_from_request()
    preds = run_kalman_filter(streams, kf_params)
    plot_div = generate_plot_div(streams, preds)

    # Calculate smoothed distance
    smoothed_distance = calculate_track_distance(preds)

    return render_template(
        "partials/map.html",
        plot_div=plot_div,
        smoothed_distance=smoothed_distance,
        original_distance=activity_data["distance"],
    )


@bp.get("/export/<string:activity_id>")
def export_gpx(activity_id: str):
    """Export smoothed GPS track as GPX file."""
    activity_data = get_activity_data(activity_id)
    streams = get_activity_streams(activity_id)
    kf_params = get_kf_params_from_request()
    preds = run_kalman_filter(streams, kf_params)

    # Get elevation and time data
    elevations = streams.get("altitude", {}).get("data", [])
    timestamps = streams.get("time", {}).get("data", [])

    # Parse start time from activity data
    start_time_str = activity_data.get("start_date")
    start_time = None
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Create GPX
    gpx = create_gpx(
        coordinates=preds,
        elevations=elevations,
        timestamps=timestamps,
        name=f"{activity_data['name']} (Smoothed)",
        description=f"Kalman-smoothed GPS track. Original activity: {activity_data['name']}",
        start_time=start_time,
    )

    # Generate filename
    activity_name = activity_data["name"].replace(" ", "_")[:50]
    filename = f"{activity_name}_smoothed.gpx"

    return Response(
        gpx_to_string(gpx),
        mimetype="application/gpx+xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def get_activity_plot(streams: dict, preds: List[Tuple[float, float]]) -> go.Figure:
    lat = [x[0] for x in streams["latlng"]["data"]]
    long = [x[1] for x in streams["latlng"]["data"]]
    z = [meters_to_feet(x) for x in streams["altitude"]["data"]]
    t = [x for x in streams["time"]["data"]]
    fig = plot_tracks_2d(lat, long, preds=preds)
    return fig


@cached(activity_info_cache)
def get_activity_data(activity_id: str) -> dict:
    return call_strava_api(f"activities/{activity_id}")


@cached(stream_cache)
def get_activity_streams(activity_id: str) -> Dict[str, Dict[str, Any]]:
    params = {
        "keys": "time,latlng,altitude,velocity_smooth,moving",
        "key_by_type": True,
        # "resolution": "high",  # high limits to 10k points; leaving it out gets all points
    }
    streams = call_strava_api(f"activities/{activity_id}/streams", params=params)
    return streams


def plot_tracks_2d(
        lat_meas: List[float],
        lon_meas: List[float],
        preds: List[Tuple[float, float]],
        zoom: float = None,
        center: Dict[str, float] = None,
):
    preds = preds or [[], []]
    zoom = zoom or get_zoom_center(lat_meas, lon_meas)[0]
    center = center or get_zoom_center(lat_meas, lon_meas)[1]

    fig = go.Figure(go.Scattermap(lat=lat_meas, lon=lon_meas, mode="markers+lines", name="Strava"))
    lat_pred = [x[0] for x in preds]
    long_pred = [x[1] for x in preds]
    fig.add_trace(go.Scattermap(lat=lat_pred, lon=long_pred, mode="lines", name="smoothed w/ Kalman filter"))

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        map=dict(
            center=go.layout.map.Center(lat=center["lat"], lon=center["lon"]),
            zoom=zoom,
        ),
    )
    return fig


def get_zoom_center(lats: List[float], lons: List[float], width_to_height: float = 4) -> Tuple[float, Dict[str, float]]:
    """Automatically get zoom and center for mapbox plot.

    Copied and modified from:
    https://stackoverflow.com/a/64148305/8844585

    Finds optimal zoom and centering for a plotly mapbox.
    Must be passed (lons & lats) or lonlats.
    Temporary solution awaiting official implementation, see:
    https://github.com/plotly/plotly.js/issues/3434

    Parameters
    --------
    lons: tuple, optional, longitude component of each location
    lats: tuple, optional, latitude component of each location
    width_to_height: float, expected ratio of final graph's with to height,
        used to select the constrained axis.  TODO: improve this parameter

    Returns
    --------
    zoom: float, from 1 to 20
    center: dict, gps position with 'lon' and 'lat' keys
    """
    maxlon, minlon = max(lons), min(lons)
    maxlat, minlat = max(lats), min(lats)
    center = {
        'lon': round((maxlon + minlon) / 2, 6),
        'lat': round((maxlat + minlat) / 2, 6)
    }

    # longitudinal range by zoom level (20 to 1)
    # in degrees, if centered at equator
    lon_zoom_range = np.array([
        0.0007, 0.0014, 0.003, 0.006, 0.012, 0.024, 0.048, 0.096,
        0.192, 0.3712, 0.768, 1.536, 3.072, 6.144, 11.8784, 23.7568,
        47.5136, 98.304, 190.0544, 360.0
    ])

    margin = 1.2
    height = (maxlat - minlat) * margin * width_to_height
    width = (maxlon - minlon) * margin
    lon_zoom = np.interp(width, lon_zoom_range, range(20, 0, -1))
    lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
    zoom = round(min(lon_zoom, lat_zoom), 2)

    return zoom, center
