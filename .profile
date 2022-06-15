# this script gets run when the app starts on Heroku
# copy the heroku config variables into the .env file
echo "SECRET_KEY=$SECRET_KEY" > /app/.env
echo "STRAVA_CLIENT_ID=$STRAVA_CLIENT_ID" >> /app/.env
echo "STRAVA_CLIENT_SECRET=$STRAVA_CLIENT_SECRET" >> /app/.env
