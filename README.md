# strava_noise_reduction

Attempting to remove noise from Strava GPX data using Kalman filters.
Very much a work in progress.

Implemented in a Flask app that connects to the Strava API.
Also very much a work in progress.
It runs but usability isn't great, it doesn't have a lot of functionality, and it's ugly as hell.

The current version of the app is available here:
https://strava-noise-reduction.herokuapp.com

## TO DO

An incomplete list of things that need to be done to make the app really usable:

Methodology/functionality:
* Fine tune the Kalman filter methodology. It works OK right now but not great. It's going to require a lot of tinkering.
* Calculate updated stats (e.g., max speed) for the activity after processing with Kalman filter.

Web app:
* Add loads of styling. It's bare bones and ugly right now.
* Improve the UI. It's really bad right now.
* Add option for exporting the smoothed GPX track and uploading to Strava. (Ideally update the original activity, but I don't think that's possible)
