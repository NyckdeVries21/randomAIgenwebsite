#!/usr/bin/env python3
"""Fill and normalize data/stats.json using entries-2026.json as source of truth for drivers/teams.

Creates a backup of `data/stats.json` and writes `data/stats.fixed.json`.
Run locally:

python scripts/fix_stats.py

"""
import json
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
ENTRIES = DATA / 'entries-2026.json'
STATS = DATA / 'stats.json'
OUT = DATA / 'stats.fixed.json'
BACK = DATA / 'stats.json.bak'

def slugify(name):
    return ''.join(c.lower() if c.isalnum() else '-' for c in (name or '')).strip('-')

def zero_season_dict():
    return {'team': None, 'points': 0, 'wins': 0, 'podiums': 0, 'poles': 0, 'fastestLaps': 0, 'position': None}

def main():
    entries = json.loads(ENTRIES.read_text(encoding='utf8'))
    stats = json.loads(STATS.read_text(encoding='utf8'))

    seasons = stats.get('seasons') or entries.get('season') and [entries.get('season')] or [2026]
    if isinstance(seasons, int):
        seasons = [seasons]

    seasons = [int(s) for s in seasons]

    # build map of entry drivers
    entry_map = {}
    for team in entries.get('teams', []):
        team_slug = team.get('slug') or slugify(team.get('name'))
        for d in team.get('drivers', []):
            driver_slug = d.get('slug') or slugify(d.get('name'))
            entry_map[driver_slug] = {'name': d.get('name'), 'team': team.get('name'), 'team_slug': team_slug}

    driverStats = deepcopy(stats.get('driverStats', {}))
    teamStats = deepcopy(stats.get('teamStats', {}))

    added_drivers = []
    filled_seasons = []

    # ensure every entry driver exists in driverStats
    for slug, info in entry_map.items():
        if slug not in driverStats:
            driverStats[slug] = {'bySeason': {}, 'allTime': {'points': 0, 'wins': 0, 'podiums': 0}}
            added_drivers.append(slug)
        # ensure seasons
        bySeason = driverStats[slug].setdefault('bySeason', {})
        for s in seasons:
            ks = str(s)
            if ks not in bySeason:
                bySeason[ks] = zero_season_dict()
                bySeason[ks]['team'] = info.get('team')
                filled_seasons.append((slug, ks))
            else:
                # ensure required keys
                for k, v in zero_season_dict().items():
                    if k not in bySeason[ks]:
                        bySeason[ks][k] = v

    # ensure every driver in stats has all seasons
    for slug, d in driverStats.items():
        bySeason = d.setdefault('bySeason', {})
        for s in seasons:
            ks = str(s)
            if ks not in bySeason:
                bySeason[ks] = zero_season_dict()
                filled_seasons.append((slug, ks))
            else:
                for k, v in zero_season_dict().items():
                    if k not in bySeason[ks]:
                        bySeason[ks][k] = v

    # ensure teams exist and have seasons
    entry_teams = { (t.get('slug') or slugify(t.get('name'))): t for t in entries.get('teams', []) }
    for team_slug, team in entry_teams.items():
        if team_slug not in teamStats:
            teamStats[team_slug] = {'bySeason': {}, 'allTime': {'points': 0, 'wins': 0}}
        for s in seasons:
            ks = str(s)
            byS = teamStats[team_slug].setdefault('bySeason', {})
            if ks not in byS:
                byS[ks] = {'points': 0, 'wins': 0, 'position': None}

    # write backup and output
    if not BACK.exists():
        BACK.write_text(STATS.read_text(encoding='utf8'), encoding='utf8')

    out = {'seasons': seasons, 'driverStats': driverStats, 'teamStats': teamStats}
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf8')

    print('Fixed stats written to', OUT)
    print('Added drivers:', added_drivers)
    print('Filled missing seasons count:', len(filled_seasons))

if __name__ == '__main__':
    main()
