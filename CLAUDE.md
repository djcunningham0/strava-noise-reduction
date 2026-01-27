# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask web application that removes noise from Strava GPS data using Kalman filters. Users authenticate via Strava OAuth, select an activity, and view interactive visualizations comparing original GPS tracks with Kalman-smoothed predictions.

Live deployment: https://strava-noise-reduction.herokuapp.com

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (development)
flask run

# Run locally (production simulation)
gunicorn wsgi:app

# Deploy to Heroku (configured via Procfile)
git push heroku main
```

## Architecture

### Flask Application Structure

Entry point: `wsgi.py` → calls `create_app()` factory in `flask_app/__init__.py`

```
flask_app/
├── __init__.py          # App factory, OAuth setup (Strava client ID: 75953)
├── config.py            # Default Kalman filter parameters
├── shared.py            # Strava API calls, unit conversions, caching
├── kalman_filter.py     # Kalman filter implementation
├── blueprints/
│   ├── auth.py          # /auth/ - OAuth login/logout
│   ├── home.py          # / - Homepage with activity list
│   ├── activity.py      # /activity/ - Activity analysis and visualization
│   └── dev.py           # /dev/ - Development/debugging endpoints
└── templates/           # Jinja2 templates with Plotly.js integration
```

### Kalman Filter Implementation

Located in `kalman_filter.py`:
- 4-dimensional state: [lat, lat_velocity, long, long_velocity]
- Uses batch filter + RTS smoother for bidirectional smoothing
- Converts lat/long to feet for matrix operations
- Configuration parameters in `config.py`: `uncertainty_pos`, `uncertainty_velo`, `state_uncertainty`, `process_uncertainty`

### Caching Strategy

In `shared.py` using `cachetools.TTLCache`:
- Activity list: 15 minutes
- Activity metadata and streams: 24 hours

## Environment Variables

Required in `.env`:
```
FLASK_APP=flask_app
FLASK_ENV=development
SECRET_KEY=[random hex string]
STRAVA_CLIENT_ID=75953
STRAVA_CLIENT_SECRET=[OAuth secret]
```

## Key Dependencies

- `filterpy` - Kalman filter implementation
- `plotly` - Interactive map visualizations
- `authlib` - Strava OAuth2 integration
- `numpy`, `scipy` - Matrix operations for filter

## Repository State

This is an active work-in-progress with exploratory artifacts:
- `streamlit_app.py`, `.streamlit/` - Alternative Streamlit UI experiments
- `Untitled.ipynb`, `tmp.py` - Scratch files for prototyping
- `example_json/`, `write_example_json.py` - Sample data generation
- `test.html`, `test.txt` - Ad-hoc testing files

These are intentionally untracked. The Flask app in `flask_app/` is the primary application.
