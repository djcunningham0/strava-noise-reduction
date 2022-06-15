from flask import Blueprint, request, render_template
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import numpy as np
import json
from typing import List, Tuple, Dict, Any

from flask_app.kalman_filter import create_kalman_filter
from flask_app.shared import call_strava_api, meters_to_feet
from flask_app import config


PREFIX = "activity"
bp = Blueprint("activity", __name__, url_prefix=f"/{PREFIX}")


@bp.post("/activity_info")
def activity_info():
    # TODO: this can get pretty intensive because it calls the API each time we hit
    #  the "recalculate" button. We should hit the API once, cache the data, and then
    #  pass that cached data into this function
    activity_id = request.form.get("activity-id")
    activity_data = get_activity_data(activity_id)
    streams = get_activity_streams(activity_id)

    # get the Kalman filter params from the request or use the defaults
    kf_params = {
        "uncertainty_pos": request.form.get("uncertainty-pos", config.DEFAULT_UNCERTAINTY_POS),
        "uncertainty_velo": request.form.get("uncertainty-velo", config.DEFAULT_UNCERTAINTY_VELO),
        "process_uncertainty": request.form.get("process-uncertainty", config.DEFAULT_PROCESS_UNCERTAINTY),
        "state_uncertainty": request.form.get("state-uncertainty", config.DEFAULT_STATE_UNCERTAINTY),
        "process_uncertainty_step": config.DEFAULT_PROCESS_UNCERTAINTY_STEP,
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


    plot_json = get_activity_plot(streams, preds)
    return render_template("activity.html", data=activity_data, plot_json=plot_json)


# @bp.post("/process_activity")
# def process_activity():
#     activity_id = request.form.get("activity-id")
#     activity_data = get_activity_data(activity_id)
#     activity_streams = get_activity_streams(activity_id)
#     json_data = {"activity-data": activity_data, "activity-streams": activity_streams}
#     return redirect(url_for(f"{PREFIX}.activity_info", json=json_data), code=307)
#     # return redirect(url_for(f"{PREFIX}.activity_info"), code=307)


def get_activity_plot(streams: dict, preds: List[Tuple[float, float]]) -> str:
    lat = [x[0] for x in streams["latlng"]["data"]]
    long = [x[1] for x in streams["latlng"]["data"]]
    z = [meters_to_feet(x) for x in streams["altitude"]["data"]]
    t = [x for x in streams["time"]["data"]]
    fig = plot_tracks_2d(lat, long, preds=preds)
    fig_json = json.dumps(fig, cls=PlotlyJSONEncoder)
    return fig_json


def get_activity_data(activity_id: str) -> dict:
    return call_strava_api(f"activities/{activity_id}")


def get_activity_streams(activity_id: str) -> Dict[str, Dict[str, Any]]:
    params = {
        "keys": "time,latlng,altitude,velocity_smooth,moving",
        "key_by_type": True,
        "resolution": "high",  # TODO: is it possible to get full resolution?
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

    fig = go.Figure(go.Scattermapbox(lat=lat_meas, lon=lon_meas, mode="markers+lines", name="Strava"))
    lat_pred = [x[0] for x in preds]
    long_pred = [x[1] for x in preds]
    fig.add_trace(go.Scattermapbox(lat=lat_pred, lon=long_pred, mode="lines", name="smoothed w/ Kalman filter"))

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        mapbox={
            "style": "stamen-terrain",
            "center": center,
            "zoom": zoom,
        }
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
