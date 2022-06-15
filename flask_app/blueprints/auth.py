from flask import Blueprint, redirect, session, url_for, current_app


PREFIX = "auth"
bp = Blueprint("auth", __name__, url_prefix=f"/{PREFIX}")


@bp.get("/login")
def login():
    redirect_uri = url_for(f"{PREFIX}.strava_auth", _external=True)
    return current_app.oauth.strava.authorize_redirect(redirect_uri)


@bp.get("/strava_auth")
def strava_auth():
    token = current_app.oauth.strava.authorize_access_token()
    session["token"] = token
    user = current_app.oauth.strava.userinfo(token=token)
    if user:
        session["user"] = user
    return redirect(url_for("homepage"))


@bp.get("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("homepage"))
