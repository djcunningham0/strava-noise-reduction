# strava_noise_reduction

Attempting to remove noise from Strava GPX data using Kalman filters.
Very much a work in progress.

Implemented in a Flask app that connects to the Strava API.
Also very much a work in progress.
It runs ~~but usability isn't great, it doesn't have a lot of functionality, and it's ugly as hell~~ and usability is decent after rewriting with Claude Code.

## TO DO

An incomplete list of things that need to be done to make the app really usable:

Methodology/functionality:
* Fine tune the Kalman filter methodology. It works OK right now but not great. It's going to require a lot of tinkering.
* Calculate updated stats (e.g., max speed) for the activity after processing with Kalman filter.
