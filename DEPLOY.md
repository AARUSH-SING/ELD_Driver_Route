# Deployment Guide

This app is ready to deploy to Railway, Render, or Heroku. Follow the steps below for your preferred platform.

## Prerequisites

- GitHub account (to push your code)
- Account on Railway, Render, or Heroku
- Git installed locally

## Step 1: Push Code to GitHub

1. Initialize Git (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit: ELD trip planner app"
   ```

2. Create a GitHub repository and push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/eld-driver-app.git
   git branch -M main
   git push -u origin main
   ```

## Step 2: Deploy to Railway.app (Recommended)

Railway has a free tier and is easiest for full-stack apps.

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `eld-driver-app` repository
4. Railway will auto-detect Django and create the deployment
5. Add environment variables in Railway dashboard:
   - `SECRET_KEY`: Generate a random key (e.g., `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: Your Railway domain (e.g., `my-app.up.railway.app`)
   - `NOMINATIM_EMAIL`: Your email address
   - `DATABASE_URL`: Railway auto-provides this if you add a PostgreSQL plugin

6. Railway deploys automatically. Get your live URL from the dashboard.

## Step 3: Deploy to Render.com (Alternative)

1. Go to [render.com](https://render.com) and sign up
2. Click **New** → **Web Service** → **Connect GitHub repo**
3. Select your `eld-driver-app` repository
4. Fill in settings:
   - **Name**: `eld-driver-app`
   - **Environment**: `Python 3`
   - **Build command**: `pip install -r requirements.txt && cd frontend && npm install && npm run build && cd ..`
   - **Start command**: `gunicorn backend.wsgi:application --log-file -`
5. Add environment variables (same as Railway above)
6. Render deploys and gives you a live `.onrender.com` URL

## Step 4: Deploy to Heroku (Free tier discontinued)

Heroku no longer offers a free tier, but if you have credits:

1. Install Heroku CLI
2. Run:
   ```bash
   heroku login
   heroku create your-app-name
   git push heroku main
   ```
3. Set environment variables:
   ```bash
   heroku config:set SECRET_KEY=your-random-key
   heroku config:set DEBUG=False
   heroku config:set NOMINATIM_EMAIL=your-email@example.com
   ```

## Step 5: Verify Your Deployment

1. Open your live URL (e.g., `https://your-app.railway.app`)
2. You should see the ELD Route & Log Planner form
3. Test with sample data:
   - Current location: `Chicago, IL`
   - Pickup: `Indianapolis, IN`
   - Dropoff: `Columbus, OH`
   - Cycle hours: `24`

## Troubleshooting

### "Geocoding service is unavailable"
- Ensure `NOMINATIM_EMAIL` environment variable is set
- Check that the server has outbound internet access to:
  - `https://nominatim.openstreetmap.org`
  - `https://geocode.maps.co`
  - `https://photon.komoot.io`

### "Static files not loading" or "Page shows 404"
- Run: `python manage.py collectstatic --no-input` (Railway/Render should do this automatically)
- Verify `frontend/dist` folder exists and is committed to Git

### "Database errors on first request"
- The `release` command in Procfile runs migrations automatically on deploy
- If it fails, SSH into your dyno/service and run manually:
  ```bash
  python manage.py migrate
  ```

## Local Testing Before Deploy

To test the production build locally:

```powershell
cd frontend
npm run build
cd ..
$env:DEBUG = "False"
$env:SECRET_KEY = "test-secret-key-only-for-testing"
python manage.py collectstatic --no-input
python manage.py runserver
```

Then visit `http://127.0.0.1:8000`

## Next Steps

After deployment, consider:
- Setting up a custom domain
- Enabling HTTPS (all platforms do this automatically)
- Monitoring logs in the deployment dashboard
- Setting up automatic deployments on Git push
