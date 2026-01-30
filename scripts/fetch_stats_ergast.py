#!/usr/bin/env python3
"""Fetch stats from Ergast API and generate data/stats.generated.json.

Usage: python scripts/fetch_stats_ergast.py

Requires: requests
"""
import json
import time
from collections import defaultdict
from pathlib import Path
from datetime import datetime

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
STATS_IN = DATA / 'stats.json'
STATS_OUT = DATA / 'stats.generated.json'
ERGAST_DIR = DATA / 'ergast'

def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d

def fetch_json(url, save_path=None, retries=3, backoff=1.0):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            headers = {'User-Agent': 'stats-fetcher/1.0 (+https://example.invalid)'}
            r = requests.get(url, timeout=15, headers=headers)
            r.raise_for_status()
            if save_path:
                save_path.write_text(r.text, encoding='utf8')
            return r.json()
        except Exception as e:
            last_err = e
            print(f'fetch_json attempt {attempt} failed for {url}:', e)
            time.sleep(backoff * attempt)
    raise last_err

def main():
    if not STATS_IN.exists():
        print('Missing', STATS_IN)
        return

    stats_src = json.loads(STATS_IN.read_text())
    seasons = stats_src.get('seasons', [])
    if not seasons:
        # default to seasons from 2000 up to current year
        current = datetime.now().year
        seasons = list(range(2000, current + 1))

    # ensure ergast cache directory exists
    ERGAST_DIR.mkdir(parents=True, exist_ok=True)

    driver_stats = {}
    team_stats = {}
    driver_info = {}

    for season in seasons:
        s = str(season)
        print('Season', s)
        # initialize per-season containers
        per_driver = defaultdict(lambda: {'points': 0.0, 'wins': 0, 'podiums': 0, 'poles': 0, 'fastestLaps': 0, 'team': None, 'position': None})
        per_team = defaultdict(lambda: {'points': 0.0, 'wins': 0, 'position': None})

        # Driver standings (final positions and points)
        try:
            ds = fetch_json(f'https://ergast.com/api/f1/{s}/driverStandings.json', save_path=ERGAST_DIR / f'ergast_{s}_driverStandings.json')
            standings = safe_get(ds, 'MRData', 'StandingsTable', 'StandingsLists', default=[])
            if standings:
                driver_list = standings[0].get('DriverStandings', [])
                for d in driver_list:
                    driverId = safe_get(d, 'Driver', 'driverId')
                    points = float(d.get('points', 0))
                    position = int(d.get('position', 0)) if d.get('position') else None
                    # normalize Ergast driverId to repo slug style: underscores -> hyphens
                    if driverId:
                        driver_slug = driverId.replace('_', '-').lower()
                    else:
                        driver_slug = None
                    per_driver[driver_slug]['points'] = points
                    per_driver[driver_slug]['position'] = position
        except Exception as e:
            print('DriverStandings error', e)

        time.sleep(0.5)

        # Constructor standings
        try:
            cs = fetch_json(f'https://ergast.com/api/f1/{s}/constructorStandings.json', save_path=ERGAST_DIR / f'ergast_{s}_constructorStandings.json')
            standings = safe_get(cs, 'MRData', 'StandingsTable', 'StandingsLists', default=[])
            if standings:
                ctor_list = standings[0].get('ConstructorStandings', [])
                for c in ctor_list:
                    ctorId = safe_get(c, 'Constructor', 'constructorId')
                    points = float(c.get('points', 0))
                    position = int(c.get('position', 0)) if c.get('position') else None
                    ctor_slug = ctorId.replace('_', '-').lower() if ctorId else None
                    per_team[ctor_slug]['points'] = points
                    per_team[ctor_slug]['position'] = position
        except Exception as e:
            print('ConstructorStandings error', e)

        time.sleep(0.5)

        # All race results for season
        try:
            res = fetch_json(f'https://ergast.com/api/f1/{s}/results.json?limit=1000', save_path=ERGAST_DIR / f'ergast_{s}_results.json')
            races = safe_get(res, 'MRData', 'RaceTable', 'Races', default=[])
            for race in races:
                results = race.get('Results', [])
                for r in results:
                    driverId = safe_get(r, 'Driver', 'driverId')
                    ctorId = safe_get(r, 'Constructor', 'constructorId')
                    pos_text = r.get('position')
                    try:
                        pos = int(pos_text) if pos_text and pos_text.isdigit() else None
                    except Exception:
                        pos = None
                    points = float(r.get('points', 0) or 0)
                    # wins
                    # normalize ids
                    driver_slug = driverId.replace('_', '-').lower() if driverId else None
                    ctor_slug = ctorId.replace('_', '-').lower() if ctorId else None
                    if pos == 1:
                        per_driver[driver_slug]['wins'] += 1
                        per_team[ctor_slug]['wins'] += 1
                        per_driver[driver_slug]['team'] = safe_get(r, 'Constructor', 'name') or per_driver[driver_slug].get('team')
                    # podiums
                    if pos and pos <= 3:
                        per_driver[driver_slug]['podiums'] += 1
                    # points
                    per_driver[driver_slug]['points'] += points
                    # fastest lap
                    fl = r.get('FastestLap')
                    if fl and fl.get('rank') in ('1', 1):
                        per_driver[driver_slug]['fastestLaps'] += 1
                        per_team[ctor_slug]['fastestLaps'] = per_team[ctor_slug].get('fastestLaps', 0) + 1
        except Exception as e:
            print('Results error', e)

        time.sleep(0.5)

        # Drivers list for season (collect basic driver info)
        try:
            dr = fetch_json(f'https://ergast.com/api/f1/{s}/drivers.json?limit=1000', save_path=ERGAST_DIR / f'ergast_{s}_drivers.json')
            drivers = safe_get(dr, 'MRData', 'DriverTable', 'Drivers', default=[])
            for d in drivers:
                driverId = d.get('driverId')
                if not driverId:
                    continue
                driver_slug = driverId.replace('_', '-').lower()
                entry = driver_info.setdefault(driver_slug, {
                    'driverId': driverId,
                    'givenName': d.get('givenName'),
                    'familyName': d.get('familyName'),
                    'dateOfBirth': d.get('dateOfBirth'),
                    'nationality': d.get('nationality'),
                    'code': d.get('code'),
                    'url': d.get('url'),
                    'seasons': []
                })
                if s not in entry['seasons']:
                    entry['seasons'].append(s)
        except Exception as e:
            print('Drivers list error', e)
        # Qualifying results for poles
        try:
            q = fetch_json(f'https://ergast.com/api/f1/{s}/qualifying.json?limit=1000', save_path=ERGAST_DIR / f'ergast_{s}_qualifying.json')
            races = safe_get(q, 'MRData', 'RaceTable', 'Races', default=[])
            for race in races:
                quals = race.get('QualifyingResults', [])
                for qual in quals:
                    driverId = safe_get(qual, 'Driver', 'driverId')
                    pos_text = qual.get('position')
                    try:
                        pos = int(pos_text) if pos_text and pos_text.isdigit() else None
                    except Exception:
                        pos = None
                    if pos == 1:
                        driver_slug = driverId.replace('_', '-').lower() if driverId else None
                        per_driver[driver_slug]['poles'] += 1
        except Exception as e:
            print('Qualifying error', e)

        # merge per-season into global structure
        for driverId, vals in per_driver.items():
            key = driverId or ''
            ds = driver_stats.setdefault(key, {'bySeason': {}, 'allTime': {}})
            pts = vals.get('points', 0)
            ds['bySeason'][s] = {
                'team': vals.get('team'),
                'points': int(pts) if float(pts).is_integer() else float(pts),
                'wins': int(vals.get('wins', 0)),
                'podiums': int(vals.get('podiums', 0)),
                'poles': int(vals.get('poles', 0)),
                'fastestLaps': int(vals.get('fastestLaps', 0)),
                'position': vals.get('position')
            }

        for ctorId, vals in per_team.items():
            key = ctorId or ''
            ts = team_stats.setdefault(key, {'bySeason': {}, 'allTime': {}})
            pts = vals.get('points', 0)
            ts['bySeason'][s] = {
                'points': int(pts) if float(pts).is_integer() else float(pts),
                'wins': int(vals.get('wins', 0)),
                'position': vals.get('position')
            }

    out = {
        'seasons': seasons,
        'driverStats': driver_stats,
        'teamStats': team_stats,
        'drivers': driver_info
    }

    # backup existing stats.json if present
    if STATS_IN.exists():
        bk = DATA / f'stats.json.bak'
        if not bk.exists():
            bk.write_text(STATS_IN.read_text())
            print('Backed up', STATS_IN, '->', bk)

    STATS_OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print('Wrote', STATS_OUT)


if __name__ == '__main__':
    main()
