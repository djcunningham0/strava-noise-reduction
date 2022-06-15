from flask import Blueprint, g, render_template
from typing import Dict, Any, List

from flask_app.shared import call_strava_api

bp = Blueprint("home", __name__)


@bp.get("/")
def homepage():
    if g.user:
        g.user["stats"] = get_stats()
    return render_template("home.html", activities=get_activities())


def get_stats() -> Dict[str, Any]:
    athlete_id = g.user["id"]
    return call_strava_api(f"athletes/{athlete_id}/stats")


def get_activities() -> List[Dict[str, str]]:
    if not g.user:
        return []
    activity_list = call_strava_api("activities")
    return [{"id": x["id"], "desc": f"{x['id']}_{x['start_date_local'][:10]}_{x['type']}_{x['name']}"}
            for x in activity_list]
