# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask web application that removes noise from Strava GPS data using Kalman filters. Users authenticate via Strava OAuth, select an activity, and view interactive visualizations comparing original GPS tracks with Kalman-smoothed predictions. Parameters can be tuned in real-time with HTMX-powered updates.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (development)
flask run
```

## Architecture

### Flask Application Structure

Entry point: `wsgi.py` -> calls `create_app()` factory in `flask_app/__init__.py`

```
flask_app/
├── __init__.py          # App factory, OAuth setup (Strava client ID: 75953)
├── config.py            # Default Kalman filter parameters
├── shared.py            # Strava API calls, token refresh, unit conversions
├── kalman_filter.py     # Kalman filter implementation
├── gpx_export.py        # GPX file generation for smoothed tracks
├── blueprints/
│   ├── auth.py          # /auth/ - OAuth login/logout
│   ├── home.py          # / - Homepage with activity list
│   └── activity.py      # /activity/ - Activity analysis, map, GPX export
└── templates/
    ├── base.html        # Base template with HTMX + Tailwind CDN
    ├── home.html        # Activity list with filtering
    ├── activity.html    # Activity view with parameter controls
    └── partials/
        └── map.html     # HTMX-swappable map partial
```

### Frontend Stack

- **Tailwind CSS** (CDN) - Utility-first styling
- **HTMX** (CDN) - Dynamic map updates without page reload
- **Plotly.js** - Interactive map visualizations

### Kalman Filter Implementation

Located in `kalman_filter.py`:
- 4-dimensional state: [lat, lat_velocity, long, long_velocity]
- Uses batch filter + RTS smoother for bidirectional smoothing
- Converts lat/long to feet for matrix operations
- Configuration parameters in `config.py`: `uncertainty_pos`, `uncertainty_velo`, `state_uncertainty`, `process_uncertainty`

### Caching Strategy

Using `cachetools.TTLCache`:
- Activity list: 15 minutes (keyed by user ID)
- Activity metadata and streams: 24 hours

### OAuth Token Refresh

`shared.py` automatically refreshes expired Strava tokens before API calls.

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
- `gpxpy` - GPX file export
- `numpy`, `scipy` - Matrix operations for filter

## Repository State

Exploratory artifacts (untracked):
- `streamlit_app.py`, `.streamlit/` - Alternative Streamlit UI experiments
- `Untitled.ipynb`, `tmp.py` - Scratch files for prototyping
- `example_json/`, `write_example_json.py` - Sample data generation
- `test.html`, `test.txt` - Ad-hoc testing files

Test data reference: `flask_app/test_activities.txt` contains activity IDs useful for testing.
