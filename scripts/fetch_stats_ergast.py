#!/usr/bin/env python3
"""Fetch stats from Ergast API and generate data/stats.generated.json.

Usage: python scripts/fetch_stats_ergast.py

Requires: requests
"""
import json
import time
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
STATS_IN = DATA / 'stats.json'
STATS_OUT = DATA / 'stats.generated.json'

def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d

def fetch_json(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

def main():
    if not STATS_IN.exists():
        print('Missing', STATS_IN)
        return

    stats_src = json.loads(STATS_IN.read_text())
    seasons = stats_src.get('seasons', [])
    if not seasons:
        seasons = list(range(2015, 2027))

    driver_stats = {}
    team_stats = {}

    for season in seasons:
        s = str(season)
        print('Season', s)
        # initialize per-season containers
        per_driver = defaultdict(lambda: {'points': 0.0, 'wins': 0, 'podiums': 0, 'poles': 0, 'fastestLaps': 0, 'team': None, 'position': None})
        per_team = defaultdict(lambda: {'points': 0.0, 'wins': 0, 'position': None})

        # Driver standings (final positions and points)
        try:
            ds = fetch_json(f'http://ergast.com/api/f1/{s}/driverStandings.json')
            standings = safe_get(ds, 'MRData', 'StandingsTable', 'StandingsLists', default=[])
            if standings:
                driver_list = standings[0].get('DriverStandings', [])
                for d in driver_list:
                    driverId = safe_get(d, 'Driver', 'driverId')
                    points = float(d.get('points', 0))
                    position = int(d.get('position', 0)) if d.get('position') else None
                    per_driver[driverId]['points'] = points
                    per_driver[driverId]['position'] = position
        except Exception as e:
            print('DriverStandings error', e)

        time.sleep(0.5)

        # Constructor standings
        try:
            cs = fetch_json(f'http://ergast.com/api/f1/{s}/constructorStandings.json')
            standings = safe_get(cs, 'MRData', 'StandingsTable', 'StandingsLists', default=[])
            if standings:
                ctor_list = standings[0].get('ConstructorStandings', [])
                for c in ctor_list:
                    ctorId = safe_get(c, 'Constructor', 'constructorId')
                    points = float(c.get('points', 0))
                    position = int(c.get('position', 0)) if c.get('position') else None
                    per_team[ctorId]['points'] = points
                    per_team[ctorId]['position'] = position
        except Exception as e:
            print('ConstructorStandings error', e)

        time.sleep(0.5)

        # All race results for season
        try:
            res = fetch_json(f'http://ergast.com/api/f1/{s}/results.json?limit=1000')
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
                    if pos == 1:
                        per_driver[driverId]['wins'] += 1
                        per_team[ctorId]['wins'] += 1
                        per_driver[driverId]['team'] = safe_get(r, 'Constructor', 'name') or per_driver[driverId].get('team')
                    # podiums
                    if pos and pos <= 3:
                        per_driver[driverId]['podiums'] += 1
                    # points
                    per_driver[driverId]['points'] += points
                    # fastest lap
                    fl = r.get('FastestLap')
                    if fl and fl.get('rank') in ('1', 1):
                        per_driver[driverId]['fastestLaps'] += 1
                        per_team[ctorId]['fastestLaps'] = per_team[ctorId].get('fastestLaps', 0) + 1
        except Exception as e:
            print('Results error', e)

        time.sleep(0.5)

        # Qualifying results for poles
        try:
            q = fetch_json(f'http://ergast.com/api/f1/{s}/qualifying.json?limit=1000')
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
                        per_driver[driverId]['poles'] += 1
        except Exception as e:
            print('Qualifying error', e)

        # merge per-season into global structure
        for driverId, vals in per_driver.items():
            ds = driver_stats.setdefault(driverId, {'bySeason': {}, 'allTime': {}})
            ds['bySeason'][s] = {
                'team': vals.get('team'),
                'points': int(vals.get('points', 0)) if float(vals.get('points', 0)).is_integer() else float(vals.get('points', 0)),
                'wins': int(vals.get('wins', 0)),
                'podiums': int(vals.get('podiums', 0)),
                'poles': int(vals.get('poles', 0)),
                'fastestLaps': int(vals.get('fastestLaps', 0)),
                'position': vals.get('position')
            }

        for ctorId, vals in per_team.items():
            ts = team_stats.setdefault(ctorId, {'bySeason': {}, 'allTime': {}})
            ts['bySeason'][s] = {
                'points': int(vals.get('points', 0)) if float(vals.get('points', 0)).is_integer() else float(vals.get('points', 0)),
                'wins': int(vals.get('wins', 0)),
                'position': vals.get('position')
            }

    out = {
        'seasons': seasons,
        'driverStats': driver_stats,
        'teamStats': team_stats
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
