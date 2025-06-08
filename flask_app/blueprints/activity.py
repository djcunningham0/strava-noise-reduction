from typing import List, Tuple, Dict, Any

import numpy as np
import plotly.graph_objects as go
import plotly.offline as pyo
from cachetools import TTLCache, cached
from flask import Blueprint, request, render_template

from flask_app.kalman_filter import create_kalman_filter
from flask_app.shared import call_strava_api, meters_to_feet
from flask_app import config


PREFIX = "activity"
bp = Blueprint("activity", __name__, url_prefix=f"/{PREFIX}")

activity_info_cache = TTLCache(maxsize=100, ttl=60 * 60 * 24)  # 24 hours
stream_cache = TTLCache(maxsize=100, ttl=60 * 60 * 24)  # 24 hours


@bp.get("/activity_info/<string:activity_id>")
def activity_info(activity_id: str):
    activity_data = get_activity_data(activity_id)
    streams = get_activity_streams(activity_id)

    # get the Kalman filter params from the request or use the defaults
    kf_params = {
        "uncertainty_pos": request.args.get("uncertainty-pos", config.DEFAULT_UNCERTAINTY_POS),
        "uncertainty_velo": request.args.get("uncertainty-velo", config.DEFAULT_UNCERTAINTY_VELO),
        "process_uncertainty": request.args.get("process-uncertainty", config.DEFAULT_PROCESS_UNCERTAINTY),
        "state_uncertainty": request.args.get("state-uncertainty", config.DEFAULT_STATE_UNCERTAINTY),
    }

    # fit the Kalman filter
    lat = [x[0] for x in streams["latlng"]["data"]]
    long = [x[1] for x in streams["latlng"]["data"]]
    z = [meters_to_feet(x) for x in streams["altitude"]["data"]]  # TODO: use altitude data
    t = [x for x in streams["time"]["data"]]  # TODO: use time data
    kf = create_kalman_filter(
        lat=lat,
        long=long,
        uncertainty_pos=float(kf_params["uncertainty_pos"]),
        uncertainty_velo=float(kf_params["uncertainty_velo"]),
        state_uncertainty_pos=float(kf_params["state_uncertainty"]),
        q_var=float(kf_params["process_uncertainty"]),
    )
    mu, cov, _, _ = kf.batch_filter(list(zip(lat, long)))
    mu, cov, _, _ = kf.rts_smoother(mu, cov)
    preds = [(x[0], x[2]) for x in mu]  # [(pred_lat_0, pred_long_0), ...)]

    fig = get_activity_plot(streams, preds)

    # if using `include_plotlyjs=False`, you must load Plotly.js separately (currently loading in `base.html` template)
    plot_div = pyo.plot(fig, output_type="div", include_plotlyjs=False)
    return render_template("activity.html", data=activity_data, plot_div=plot_div)


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
