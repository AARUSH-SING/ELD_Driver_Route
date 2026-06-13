# Driver ELD Planner

A full-stack Django + React app for drivers to plan routes and visualize ELD log sheets.

## Features

- Route planning with OpenStreetMap and OSRM
- Log sheet generation for 70-hour/8-day property-carrier drivers
- Route instructions and rest/fuel stop guidance
- Mobile-friendly React UI with Leaflet map
- Ready for cloud deployment (Railway, Render, Heroku)

## Quick Start

### 1. Backend Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

### 2. Frontend Build

```powershell
cd frontend
npm install
npm run build
cd ..
```

### 3. Run Locally

```powershell
$env:NOMINATIM_EMAIL = 'your-email@example.com'
$env:DEBUG = 'True'
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

### 4. Development Mode (with hot reload)

**Terminal 1 - Backend:**
```powershell
$env:NOMINATIM_EMAIL = 'your-email@example.com'
python manage.py runserver
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

Visit http://127.0.0.1:5173 for the dev frontend (proxies API to localhost:8000)

## Deployment

Ready to go live? See **[DEPLOY.md](DEPLOY.md)** for:
- Step-by-step Railway.app deployment (recommended)
- Render.com alternative
- Heroku setup
- Environment variable configuration
- Troubleshooting

## Environment Variables

| Variable | Required | Default | Example |
|----------|----------|---------|---------|
| `DEBUG` | No | `True` | `False` (for production) |
| `SECRET_KEY` | Yes (production) | Auto-generated | `django-insecure-...` |
| `ALLOWED_HOSTS` | No | `127.0.0.1,localhost` | `my-app.railway.app` |
| `NOMINATIM_EMAIL` | No | None | `your-email@example.com` |
| `DATABASE_URL` | No | SQLite | `postgresql://user:pass@host/db` |

## API Endpoints

- `POST /api/trip/` - Plan a trip and generate ELD logs
  - Request body:
    ```json
    {
      "current_location": "Chicago, IL",
      "pickup_location": "Indianapolis, IN",
      "dropoff_location": "Columbus, OH",
      "current_cycle_used": 24
    }
    ```
  - Returns: Route data, stops, and daily log sheets

- `GET /health/` - Backend health check
  - Returns: `{"status": "ok"}`

## Troubleshooting

### "Geocoding service is unavailable"
- Set `NOMINATIM_EMAIL` environment variable
- Ensure server has outbound internet access to:
  - `nominatim.openstreetmap.org`
  - `geocode.maps.co`
  - `photon.komoot.io`

### "Static files not loading" or "404 page"
- Run: `python manage.py collectstatic --no-input`
- Verify `frontend/dist/` folder exists
- Check that `frontend/dist/` is committed to Git

### Frontend shows "Network Error"
- Verify Django backend is running on `http://127.0.0.1:8000`
- In dev mode, Vite should proxy `/api` requests automatically
- Check browser DevTools Network tab for request details

## Architecture

- **Backend**: Django 6.0 + Django REST Framework
- **Frontend**: React 18 + Vite + Leaflet (mapping)
- **Geocoding**: Nominatim → geocode.maps.co → Photon (fallback chain)
- **Routing**: OSRM (Open Route Service Map)
- **Database**: SQLite (local) or PostgreSQL (production)

## Notes

- The app requires outbound internet access for geocoding and routing
- All external APIs used are free and open-source
- Frontend is pre-built in `frontend/dist/` and served by Django
- WhiteNoise handles static file serving in production
