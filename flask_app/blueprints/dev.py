"""
This should be removed in the final version. It's just a convenient way to see what gets
returned by requests to the Strava API inside the app.
"""

from flask import Blueprint, jsonify, render_template, request
import json

from flask_app.shared import call_strava_api


PREFIX = "dev"
bp = Blueprint("dev", __name__, url_prefix=f"/{PREFIX}")


@bp.get("/")
def dev_home():
    return render_template("dev.html")


@bp.post("/api")
def strava_api():
    endpoint = request.form.get("endpoint")
    params = request.form.get("params") or "{}"
    params = json.loads(params)
    out = [{"endpoint": endpoint, "params": params}, call_strava_api(uri=endpoint, params=params)]
    return jsonify(out)
