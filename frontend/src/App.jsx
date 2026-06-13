import { useState } from 'react'
import axios from 'axios'
import { MapContainer, TileLayer, Polyline, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})
L.Marker.prototype.options.icon = defaultIcon

const statusClass = {
  Driving: 'bar-driving',
  'On Duty (Not Driving)': 'bar-on-duty',
  'Off Duty': 'bar-off-duty',
}

function formatTime(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function App() {
  const [form, setForm] = useState({
    current_location: 'Chicago, IL',
    pickup_location: 'Indianapolis, IN',
    dropoff_location: 'Columbus, OH',
    current_cycle_used: 24,
  })
  const [trip, setTrip] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setTrip(null)
    try {
      const response = await axios.post('/api/trip/', form)
      setTrip(response.data)
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        (err.message === 'Network Error'
          ? 'Network Error: unable to reach backend. Ensure the Django server is running at http://127.0.0.1:8000.'
          : err.message)
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const routeCoords = trip?.route?.geometry?.coordinates?.map(([lon, lat]) => [lat, lon]) || []
  const center = routeCoords.length ? routeCoords[Math.floor(routeCoords.length / 2)] : [41.88, -87.63]

  return (
    <div className="page-shell">
      <header>
        <div>
          <h1>ELD Route & Log Planner</h1>
          <p>Plan a property-carrier trip and generate filled Daily Log Sheets for a 70-hour/8-day cycle.</p>
        </div>
      </header>

      <main>
        <section className="form-panel">
          <form onSubmit={handleSubmit}>
            <label>
              Current location
              <input name="current_location" value={form.current_location} onChange={handleChange} />
            </label>
            <label>
              Pickup location
              <input name="pickup_location" value={form.pickup_location} onChange={handleChange} />
            </label>
            <label>
              Dropoff location
              <input name="dropoff_location" value={form.dropoff_location} onChange={handleChange} />
            </label>
            <label>
              Current cycle used (hrs)
              <input
                name="current_cycle_used"
                type="number"
                min="0"
                max="70"
                value={form.current_cycle_used}
                onChange={handleChange}
              />
            </label>
            <button type="submit" disabled={loading}>{loading ? 'Planning...' : 'Plan Trip'}</button>
          </form>
          {error && <div className="alert">{error}</div>}
        </section>

        {trip && (
          <section className="results-panel">
            <div className="summary-card">
              <div>
                <strong>Total route:</strong> {trip.route.distance_miles} miles
              </div>
              <div>
                <strong>Drive time:</strong> {trip.route.duration_hours} hrs
              </div>
              <div>
                <strong>Cycle hours used:</strong> {trip.cycle_used_hours} / {trip.cycle_limit}
              </div>
            </div>

            <div className="map-card">
              <MapContainer center={center} zoom={6} scrollWheelZoom={false} className="map">
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {routeCoords.length > 0 && <Polyline positions={routeCoords} color="#1a73e8" weight={5} />}
                {trip.stops.map((stop, index) => stop.lat && stop.lon ? (
                  <Marker key={index} position={[stop.lat, stop.lon]}>
                    <Popup>{stop.type}: {stop.location}</Popup>
                  </Marker>
                ) : null)}
              </MapContainer>
            </div>

            <div className="details-grid">
              <div className="instructions-card">
                <h2>Route instructions</h2>
                <ol>
                  {trip.route.instructions.slice(0, 12).map((step, index) => (
                    <li key={index}>
                      {step.instruction} — {step.distance_miles} mi, {step.duration_hours} hr
                    </li>
                  ))}
                </ol>
              </div>
              <div className="stops-card">
                <h2>Stops & rests</h2>
                <ul>
                  {trip.stops.map((stop, index) => (
                    <li key={index}><strong>{stop.type}</strong> — {stop.location}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="log-card">
              <h2>Daily Log Sheets</h2>
              {trip.log_days.map((day) => (
                <div key={day.day_label} className="log-sheet">
                  <div className="log-header">
                    <strong>{day.day_label}</strong>
                    <span>Driving: {day.totals.Driving.toFixed(2)} hr</span>
                    <span>On duty: {day.totals['On Duty (Not Driving)'].toFixed(2)} hr</span>
                    <span>Off duty: {day.totals['Off Duty'].toFixed(2)} hr</span>
                  </div>
                  <div className="hour-grid">
                    {Array.from({ length: 24 }).map((_, hour) => (
                      <div key={hour} className="hour-cell">{hour}</div>
                    ))}
                  </div>
                  <div className="log-row">
                    {day.events.map((event, idx) => {
                      const width = ((event.end_minute - event.start_minute) / 1440) * 100
                      const left = (event.start_minute / 1440) * 100
                      return (
                        <div
                          key={idx}
                          className={`log-block ${statusClass[event.status] || 'bar-on-duty'}`}
                          style={{ width: `${width}%`, left: `${left}%` }}
                        >
                          <span>{event.label}</span>
                          <small>{formatTime(event.start_minute)}–{formatTime(event.end_minute)}</small>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
