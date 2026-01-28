"""GPX file generation for smoothed GPS tracks."""

from datetime import datetime, timezone
from typing import List, Tuple, Optional

import gpxpy
import gpxpy.gpx


def create_gpx(
    coordinates: List[Tuple[float, float]],
    elevations: Optional[List[float]] = None,
    timestamps: Optional[List[int]] = None,
    name: str = "Smoothed Track",
    description: str = "GPS track smoothed with Kalman filter",
    start_time: Optional[datetime] = None,
) -> gpxpy.gpx.GPX:
    """Create a GPX object from smoothed coordinates.

    Parameters
    ----------
    coordinates : List of (latitude, longitude) tuples
    elevations : Optional list of elevation values in meters
    timestamps : Optional list of elapsed seconds from start
    name : Track name
    description : Track description
    start_time : Activity start time (defaults to now)

    Returns
    -------
    gpxpy.gpx.GPX object ready to be exported
    """
    gpx = gpxpy.gpx.GPX()
    gpx.name = name
    gpx.description = description
    gpx.creator = "GPX Noise Reduction - Kalman Filter"

    # Create track
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.name = name
    gpx.tracks.append(gpx_track)

    # Create segment
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    # Set start time
    if start_time is None:
        start_time = datetime.now(timezone.utc)
    elif start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    # Add points
    for i, (lat, lon) in enumerate(coordinates):
        point = gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon)

        if elevations and i < len(elevations):
            point.elevation = elevations[i]

        if timestamps and i < len(timestamps):
            from datetime import timedelta
            point.time = start_time + timedelta(seconds=timestamps[i])

        gpx_segment.points.append(point)

    return gpx


def gpx_to_string(gpx: gpxpy.gpx.GPX) -> str:
    """Convert GPX object to XML string."""
    return gpx.to_xml()
