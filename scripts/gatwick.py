#!/usr/bin/env python3
"""Retrieve Gatwick aerodrome weather. Do not invent delays/cancellations.

Flight status is intentionally linked to Gatwick's official flight board: its public
HTML is not a stable licensed API for bulk airport-wide delay statistics.
"""
import datetime as dt
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / 'data' / 'gatwick.json'
URL = 'https://aviationweather.gov/api/data/metar?ids=EGKK&format=json'
NOW = dt.datetime.now(dt.timezone.utc)


def collect(previous=None):
    previous = previous or {}
    output = {
        'airport': 'London Gatwick', 'iata': 'LGW', 'icao': 'EGKK',
        'checked_at': NOW.isoformat().replace('+00:00', 'Z'),
        'source': 'NOAA Aviation Weather Center METAR',
        'source_url': 'https://aviationweather.gov/data/api/',
        'official_flights_url': 'https://www.gatwickairport.com/flights',
        'official_departures_url': 'https://www.gatwickairport.com/flights?destination=D',
        'official_arrivals_url': 'https://www.gatwickairport.com/flights?destination=A',
        'delay_count': None, 'cancellation_count': None,
        'delay_status': 'Not available from an approved live statistics feed',
        'status': 'unavailable', 'metar': None,
    }
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'NI-Crisis-Watch/1.1 (public weather monitoring)', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read(200000).decode('utf-8'))
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            raise ValueError('No METAR observation supplied')
        item = payload[0]
        if item.get('icaoId') and item['icaoId'] != 'EGKK':
            raise ValueError('Unexpected airport identifier')
        obs = item.get('obsTime')
        when = dt.datetime.fromtimestamp(obs, dt.timezone.utc) if isinstance(obs,(int,float)) else None
        if when is None and isinstance(item.get('reportTime'), str):
            when = dt.datetime.fromisoformat(item['reportTime'].replace('Z','+00:00'))
        if when is None or when.tzinfo is None or not (0 <= (NOW-when).total_seconds() <= 6 * 3600):
            raise ValueError('Weather observation missing or stale')
        output['status'] = 'ok'
        output['last_success'] = output['checked_at']
        output['metar'] = {
            'observed_at': when.isoformat().replace('+00:00','Z'),
            'raw': str(item.get('rawOb',''))[:350],
            'wind_kt': item.get('wspd'),
            'gust_kt': item.get('wgst'),
            'visibility_miles': item.get('visib'),
            'flight_category': item.get('fltCat'),
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        output['problem'] = type(exc).__name__
        output['last_success'] = previous.get('last_success')
        # Do not carry a previously captured weather observation forward as live.
    return output


def main():
    previous = {}
    if TARGET.exists():
        try: previous = json.loads(TARGET.read_text(encoding='utf-8'))
        except (OSError, ValueError): pass
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    out = collect(previous)
    TARGET.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Gatwick weather:', out['status'], 'as of', out['checked_at'])


if __name__ == '__main__':
    main()
