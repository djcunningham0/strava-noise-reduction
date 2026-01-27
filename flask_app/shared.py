import os
import json
import time
from flask import current_app, session
import requests


def refresh_token_if_needed() -> dict:
    """Check if OAuth token is expired and refresh if necessary.

    Returns the current valid token (refreshed if needed).
    """
    token = session.get("token")
    if not token:
        return None

    # Check if token is expired (with 60 second buffer)
    expires_at = token.get("expires_at", 0)
    if time.time() < expires_at - 60:
        return token

    # Token is expired or about to expire, refresh it
    print("Token expired, refreshing...")
    refresh_response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": os.getenv("STRAVA_CLIENT_ID"),
            "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
            "grant_type": "refresh_token",
            "refresh_token": token.get("refresh_token"),
        },
    )
    refresh_response.raise_for_status()
    new_token = refresh_response.json()

    # Update session with new token
    session["token"] = new_token
    print("Token refreshed successfully")
    return new_token


def call_strava_api(uri: str, method: str = "get", **kwargs) -> dict:
    """Hit any endpoint for the Strava API."""
    token = refresh_token_if_needed()
    print(f"calling Strava API at: {os.path.join(current_app.oauth.strava.api_base_url, uri)}")
    r = current_app.oauth.strava.request(
        method=method,
        url=uri,
        token=token,
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
