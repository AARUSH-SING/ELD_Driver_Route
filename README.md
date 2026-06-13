# Driver ELD Planner

A full-stack Django + React app for drivers to plan routes and visualize ELD log sheets.

## Features

- Route planning with OpenStreetMap and OSRM
- Log sheet generation for 70-hour/8-day property-carrier drivers
- Route instructions and rest/fuel stop guidance
- Mobile-friendly React UI with Leaflet map

## Setup

### Backend

1. Create a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run Django server:
   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

If Nominatim geocoding returns `403 Forbidden`, set a valid contact email before starting the backend:
```powershell
$env:NOMINATIM_EMAIL = 'your-email@example.com'
python manage.py runserver
```

The backend also now falls back to additional open free geocoding services if Nominatim is unavailable, but the app still requires outbound internet access for geocoding and routing.

### Frontend

1. Change into the frontend folder:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

2. The frontend uses a Vite proxy for `/api` requests and forwards them to the Django backend at `http://127.0.0.1:8000`.

### Usage

Open the React app in your browser, enter current location, pickup, dropoff, and current cycle hours, then submit.

### Backend health check

Verify the backend is running by opening `http://127.0.0.1:8000/health/` in your browser. It should return `{"status": "ok"}`.
