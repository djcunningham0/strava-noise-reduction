from flask import Blueprint, g, render_template
from typing import Dict, Any, List
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from flask_app.shared import call_strava_api

bp = Blueprint("home", __name__)

activities_cache = TTLCache(maxsize=100, ttl=60 * 15)  # 15 minutes


@bp.get("/")
def homepage():
    if g.user:
        g.user["stats"] = get_stats()
        activities = get_activities_for_user(g.user["id"])
    else:
        activities = []
    return render_template("home.html", activities=activities)


def get_stats() -> Dict[str, Any]:
    athlete_id = g.user["id"]
    return call_strava_api(f"athletes/{athlete_id}/stats")


def _has_gps_data(activity: Dict[str, Any]) -> bool:
    """Check if activity has GPS data (not manually entered)."""
    if activity.get("manual"):
        return False
    start_latlng = activity.get("start_latlng")
    # start_latlng is [] for manual activities, [lat, lng] for GPS activities
    return isinstance(start_latlng, list) and len(start_latlng) == 2


def _is_virtual_activity(activity: Dict[str, Any]) -> bool:
    """Check if activity is virtual (indoor trainer, etc.)."""
    return activity.get("type", "").startswith("Virtual")


@cached(activities_cache, key=lambda user_id: hashkey(user_id))
def get_activities_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Fetch activities for a user (cached by user_id).

    Excludes virtual activities and activities without GPS data.
    """
    activity_list = call_strava_api("activities")
    return [
        {
            "id": x["id"],
            "name": x["name"],
            "type": x["type"],
            "sport_type": x.get("sport_type", x["type"]),
            "date": x["start_date_local"][:10],
            "distance": x.get("distance", 0),
            "moving_time": x.get("moving_time", 0),
            "total_elevation_gain": x.get("total_elevation_gain", 0),
        }
        for x in activity_list
        if _has_gps_data(x) and not _is_virtual_activity(x)
    ]
