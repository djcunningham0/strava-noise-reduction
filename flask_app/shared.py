import os
import json
from flask import current_app, session


def call_strava_api(uri: str, method: str = "get", **kwargs) -> dict:
    """Hit any endpoint for the Strava API"""
    print(f"calling Strava API at: {os.path.join(current_app.oauth.strava.api_base_url, uri)}")
    r = current_app.oauth.strava.request(
        method=method,
        url=uri,
        token=session.get("token"),
        **kwargs
    )
    r.raise_for_status()
    return r.json()


def meters_to_feet(x: float) -> float:
    return x * 100 / 2.54 / 12


def meters_to_miles(x: float) -> float:
    return meters_to_feet(x) / 5280


def meters_per_second_to_mph(x: float) -> float:
    return meters_to_miles(x) * 3600


def seconds_to_time(s: float, allow_decimal_seconds: bool = False) -> str:
    hours = s // 3600
    minutes = (s - 3600 * hours) // 60
    seconds = s - 3600 * hours - 60 * minutes
    seconds = seconds if allow_decimal_seconds else int(round(seconds))
    return f"{int(hours):02}:{int(minutes):02}:{seconds:02}"


def pretty_print_json(value) -> str:
    return json.dumps(value, sort_keys=True, indent=4, separators=(',', ': '))
