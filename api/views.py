import math
import os
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
GEOCODE_FALLBACK_URL = 'https://geocode.maps.co/search'
PHOTON_URL = 'https://photon.komoot.io/api/'
OSRM_URL = 'https://router.project-osrm.org/route/v1/driving'
NOMINATIM_EMAIL = os.environ.get('NOMINATIM_EMAIL')
NOMINATIM_USER_AGENT = os.environ.get(
    'NOMINATIM_USER_AGENT',
    'Driver ELD Planner/1.0 (+https://localhost/)'
)


def parse_coordinate(value):
    try:
        parts = [part.strip() for part in value.split(',')]
        if len(parts) == 2:
            lat = float(parts[0])
            lon = float(parts[1])
            return {'lat': lat, 'lon': lon}
    except ValueError:
        return None
    return None


def geocode_location(value):
    coords = parse_coordinate(value)
    if coords:
        return coords

    payload = {
        'q': value,
        'format': 'json',
        'limit': 1,
        'accept-language': 'en',
    }
    if NOMINATIM_EMAIL:
        payload['email'] = NOMINATIM_EMAIL

    headers = {
        'User-Agent': NOMINATIM_USER_AGENT,
        'Accept': 'application/json',
        'Referer': 'http://localhost',
    }

    try:
        resp = requests.get(NOMINATIM_URL, params=payload, headers=headers, timeout=15)
    except requests.RequestException:
        return geocode_location_fallback(value)

    if resp.status_code != 200:
        return geocode_location_fallback(value)

    data = resp.json()
    if not data:
        return geocode_location_fallback(value)
    item = data[0]
    return {'lat': float(item['lat']), 'lon': float(item['lon']), 'name': item.get('display_name', value)}


def geocode_location_fallback(value):
    try:
        return geocode_location_mapsco(value)
    except (requests.RequestException, ValueError):
        return geocode_location_photon(value)


def geocode_location_mapsco(value):
    payload = {
        'q': value,
        'format': 'json',
        'limit': 1,
    }
    headers = {
        'User-Agent': NOMINATIM_USER_AGENT,
        'Accept': 'application/json',
    }
    resp = requests.get(GEOCODE_FALLBACK_URL, params=payload, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise ValueError(f'Geocoding failed: {resp.status_code} {resp.reason}')
    data = resp.json()
    if not data:
        raise ValueError(f'Unable to geocode location: {value}')
    item = data[0]
    return {'lat': float(item['lat']), 'lon': float(item['lon']), 'name': item.get('display_name', value)}


def geocode_location_photon(value):
    params = {
        'q': value,
        'limit': 1,
    }
    headers = {
        'User-Agent': NOMINATIM_USER_AGENT,
        'Accept': 'application/json',
    }
    resp = requests.get(PHOTON_URL, params=params, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise ValueError(f'Geocoding failed: {resp.status_code} {resp.reason}')
    data = resp.json()
    if not data.get('features'):
        raise ValueError(f'Unable to geocode location: {value}')
    feature = data['features'][0]
    coords = feature.get('geometry', {}).get('coordinates') or []
    if len(coords) < 2:
        raise ValueError(f'Unable to geocode location: {value}')
    return {'lat': float(coords[1]), 'lon': float(coords[0]), 'name': feature.get('properties', {}).get('name', value)}


def meters_to_miles(value):
    return round(value * 0.000621371, 2)


def seconds_to_hours(value):
    return round(value / 3600.0, 2)


def clamp_log_event(event, day, segments):
    segments.append({
        'day': day,
        'status': event['status'],
        'label': event.get('label', ''),
        'start_minute': event['start_minute'],
        'end_minute': event['end_minute'],
        'duration_hours': round((event['end_minute'] - event['start_minute']) / 60.0, 2),
    })


class HealthCheckAPIView(APIView):
    def get(self, request):
        return Response({'status': 'ok'})


class TripPlanAPIView(APIView):
    def post(self, request):
        payload = request.data
        required = ['current_location', 'pickup_location', 'dropoff_location', 'current_cycle_used']
        if not all(key in payload for key in required):
            return Response({'detail': 'Missing required inputs.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            current_cycle_used = float(payload['current_cycle_used'])
        except (ValueError, TypeError):
            return Response({'detail': 'Current cycle used must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            origin = geocode_location(payload['current_location'])
            pickup = geocode_location(payload['pickup_location'])
            dropoff = geocode_location(payload['dropoff_location'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except requests.RequestException as exc:
            return Response(
                {'detail': f'Geocoding service is unavailable: {str(exc)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        locations = [origin, pickup, dropoff]
        coords = ';'.join([f"{loc['lon']},{loc['lat']}" for loc in locations])
        route_url = f'{OSRM_URL}/{coords}'
        params = {'overview': 'full', 'geometries': 'geojson', 'steps': 'true'}

        try:
            response = requests.get(route_url, params=params, timeout=20)
            response.raise_for_status()
            route_data = response.json()
        except requests.RequestException:
            return Response({'detail': 'Routing service is unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if 'routes' not in route_data or not route_data['routes']:
            return Response({'detail': 'Unable to calculate route.'}, status=status.HTTP_400_BAD_REQUEST)

        route = route_data['routes'][0]
        distance_miles = meters_to_miles(route['distance'])
        duration_hours = seconds_to_hours(route['duration'])
        geometry = route['geometry']
        instructions = []
        for leg_idx, leg in enumerate(route['legs']):
            for step in leg['steps']:
                instructions.append({
                    'instruction': step.get('maneuver', {}).get('instruction', step.get('name', 'Continue')),
                    'distance_miles': meters_to_miles(step.get('distance', 0)),
                    'duration_hours': seconds_to_hours(step.get('duration', 0)),
                })

        leg_distances = [meters_to_miles(leg['distance']) for leg in route['legs']]
        leg_durations = [seconds_to_hours(leg['duration']) for leg in route['legs']]

        legs = [
            {'type': 'drive', 'label': 'Drive to pickup', 'duration_hours': leg_durations[0], 'distance_miles': leg_distances[0]},
            {'type': 'on_duty', 'label': 'Pickup and paperwork', 'duration_hours': 1.0, 'distance_miles': 0},
            {'type': 'drive', 'label': 'Drive to dropoff', 'duration_hours': leg_durations[1], 'distance_miles': leg_distances[1]},
            {'type': 'on_duty', 'label': 'Dropoff and paperwork', 'duration_hours': 1.0, 'distance_miles': 0},
        ]

        stops = [
            {'type': 'Start', 'location': origin.get('name', payload['current_location']), 'lat': origin['lat'], 'lon': origin['lon']},
            {'type': 'Pickup', 'location': pickup.get('name', payload['pickup_location']), 'lat': pickup['lat'], 'lon': pickup['lon']},
            {'type': 'Dropoff', 'location': dropoff.get('name', payload['dropoff_location']), 'lat': dropoff['lat'], 'lon': dropoff['lon']},
        ]

        if distance_miles > 1000:
            mid_lat = None
            mid_lon = None
            coords_list = geometry.get('coordinates', [])
            if coords_list:
                mid_idx = len(coords_list) // 2
                mid_lon, mid_lat = coords_list[mid_idx]
            stops.append({
                'type': 'Refuel',
                'location': 'Fuel stop recommended near midpoint',
                'lat': mid_lat,
                'lon': mid_lon
            })

        log_days = []
        current_minute = 8 * 60  # Absolute cumulative minutes from start of Day 1
        drive_since_rest = 0     # Driving minutes since last 10-hour rest (limit 11 hours)
        drive_since_break = 0    # Driving minutes since last 30-minute break (limit 8 hours)
        window_start = current_minute
        window_end = window_start + 14 * 60
        remain_cycle = current_cycle_used
        log_events = []

        def add_event(status, duration_minutes, label=''):
            nonlocal current_minute
            remaining_minutes = duration_minutes
            while remaining_minutes > 0:
                day_start_minute = (current_minute // 1440) * 1440
                end_of_day = day_start_minute + 1440
                span = min(remaining_minutes, end_of_day - current_minute)
                
                day_index = int(current_minute // 1440) + 1
                
                event = {
                    'status': status,
                    'label': label,
                    'start_minute': int(current_minute - day_start_minute),
                    'end_minute': int((current_minute + span) - day_start_minute),
                }
                clamp_log_event(event, day_index, log_events)
                current_minute += span
                remaining_minutes -= span

        def enforce_off_duty(mins=600):
            nonlocal drive_since_break, drive_since_rest, window_start, window_end
            add_event('Off Duty', mins, 'Required rest')
            drive_since_break = 0
            drive_since_rest = 0
            window_start = current_minute
            window_end = window_start + 14 * 60

        for leg in legs:
            remain = int(leg['duration_hours'] * 60)
            if leg['type'] == 'drive':
                while remain > 0:
                    # 70-hour cycle limit check (reset cycle by 34-hour restart)
                    if remain_cycle >= 70.0:
                        enforce_off_duty(34 * 60)
                        remain_cycle = 0.0
                        continue
                    
                    # 14-hour daily duty window limit check
                    # 11-hour driving limit check (uses drive_since_rest)
                    if current_minute >= window_end or drive_since_rest >= 11 * 60:
                        enforce_off_duty(600)
                        continue
                    
                    # 30-minute break check
                    if drive_since_break >= 8 * 60:
                        add_event('Off Duty', 30, '30-min break')
                        drive_since_break = 0
                        continue
                    
                    # Driving time remaining to next break/limit
                    limit_to_break = 8 * 60 - drive_since_break
                    limit_to_cycle = max(0.0, (70.0 - remain_cycle) * 60)
                    
                    available = min(
                        remain,
                        (11 * 60 - drive_since_rest),
                        (window_end - current_minute),
                        limit_to_break,
                        limit_to_cycle
                    )
                    
                    if available <= 0:
                        # If cycle is depleted, trigger 34-hr restart. Otherwise daily rest.
                        if limit_to_cycle <= 0:
                            enforce_off_duty(34 * 60)
                            remain_cycle = 0.0
                        else:
                            enforce_off_duty(600)
                        continue
                        
                    add_event('Driving', available, leg['label'])
                    remain -= available
                    drive_since_rest += available
                    drive_since_break += available
                    remain_cycle += available / 60.0
            else:
                # On-duty leg
                # If on-duty leg itself is >= 30 minutes, it counts as a break for the 8-hour limit!
                if remain >= 30:
                    drive_since_break = 0
                    
                while remain > 0:
                    end_of_day = ((current_minute // 1440) + 1) * 1440
                    available = min(remain, end_of_day - current_minute)
                    add_event('On Duty (Not Driving)', available, leg['label'])
                    remain -= available
                    remain_cycle += available / 60.0

        for event in log_events:
            day_index = event['day']
            while len(log_days) < day_index:
                log_days.append({
                    'day_label': f'Day {len(log_days) + 1}',
                    'events': [],
                    'totals': {'Driving': 0, 'On Duty (Not Driving)': 0, 'Off Duty': 0}
                })
            log_days[day_index - 1]['events'].append(event)
            log_days[day_index - 1]['totals'][event['status']] += event['duration_hours']

        return Response({
            'route': {
                'distance_miles': distance_miles,
                'duration_hours': duration_hours,
                'geometry': geometry,
                'instructions': instructions,
                'legs': legs,
            },
            'log_days': log_days,
            'stops': stops,
            'cycle_used_hours': round(remain_cycle, 2),
            'cycle_limit': 70,
        })
