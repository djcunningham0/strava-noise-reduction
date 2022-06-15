import os
from flask import Flask, session, g
from authlib.integrations.flask_client import OAuth

from flask_app.shared import (
    pretty_print_json,
    meters_to_miles,
    meters_to_feet,
    seconds_to_time,
    meters_per_second_to_mph,
)


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(SECRET_KEY=os.getenv("SECRET_KEY"))

    # set up Strava oauth service and attach to app context so it can be used in blueprints
    with app.app_context():
        app.oauth = OAuth(app)
        app.oauth.register(
            name="strava",
            client_id=os.getenv("STRAVA_CLIENT_ID"),
            client_secret=os.getenv("STRAVA_CLIENT_SECRET"),
            api_base_url="https://www.strava.com/api/v3/",
            authorization_endpoint="http://www.strava.com/oauth/authorize",
            token_endpoint="https://www.strava.com/api/v3/oauth/token",
            userinfo_endpoint="athlete",
            redirect_uri="http://127.0.0.1:5000/auth/strava_auth",  # TODO need this?
            client_kwargs={
                'response_type': 'code',
                'scope': 'read,read_all,profile:read_all,activity:read_all',
                'token_endpoint_auth_method': 'client_secret_post',
            },
        )

    # register blueprints
    from flask_app.blueprints import home, auth, activity, dev
    app.register_blueprint(home.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(activity.bp)
    app.register_blueprint(dev.bp)
    app.add_url_rule("/", endpoint="homepage")

    # use functions in jinja2 templates
    app.jinja_env.globals.update(
        pretty_print_json=pretty_print_json,
        meters_to_miles=meters_to_miles,
        meters_to_feet=meters_to_feet,
        seconds_to_time=seconds_to_time,
        meters_per_second_to_mph=meters_per_second_to_mph,
    )

    @app.before_request
    def load_user():
        user = session.get("user")
        if user:
            g.user = user
        else:
            g.user = None

    return app
