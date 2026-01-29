import json
from pathlib import Path
from copy import deepcopy

root = Path(__file__).resolve().parent.parent
stats_path = root / 'data' / 'stats.json'
entries_path = root / 'data' / 'entries-2026.json'
backup_path = root / 'data' / 'stats.json.bak'
out_path = root / 'data' / 'stats.updated.json'

def normalize(s):
    return ''.join(c.lower() if c.isalnum() else '-' for c in (s or '')).strip('-')

def load(p):
    return json.loads(p.read_text(encoding='utf8'))

stats = load(stats_path)
entries = load(entries_path)

seasons = stats.get('seasons', [])
driverStats = stats.setdefault('driverStats', {})
teamStats = stats.setdefault('teamStats', {})

# build mapping of entry driver -> team (current 2026)
entry_map = {}
team_name_by_slug = {}
for team in entries.get('teams', []):
    tslug = team.get('slug') or normalize(team.get('name'))
    team_name_by_slug[tslug] = team.get('name')
    for d in team.get('drivers', []):
        dslug = d.get('slug') or normalize(d.get('name'))
        entry_map[dslug] = {'name': d.get('name'), 'teamSlug': tslug, 'teamName': team.get('name')}

# helper: attempt to guess team name for a driver in a given season by searching existing stats
def guess_team_name_for(season, driver_slug, default_team_slug=None):
    # prefer explicit team in driver's bySeason if present
    d = driverStats.get(driver_slug)
    if d:
        bs = d.get('bySeason') or {}
        if str(season) in bs and bs[str(season)].get('team'):
            return bs[str(season)].get('team')
    # otherwise, search other drivers for same normalized team name in that season
    # build map seasonTeamName -> occurrences
    for other_slug, od in driverStats.items():
        if other_slug == driver_slug: continue
        obs = od.get('bySeason') or {}
        s = obs.get(str(season))
        if s and s.get('team'):
            # if this other driver shares team slug with default_team_slug, return that name
            if default_team_slug:
                if normalize(s.get('team')).find(default_team_slug) != -1 or default_team_slug.find(normalize(s.get('team'))) != -1:
                    return s.get('team')
    # fallback: use team name from entries current mapping
    if default_team_slug and default_team_slug in team_name_by_slug:
        return team_name_by_slug[default_team_slug]
    return None

created = {'driversAdded': [], 'driverSeasonsAdded': [], 'teamsSeasonsAdded': []}

# Ensure all drivers from entries exist in stats.driverStats
for dslug, info in entry_map.items():
    if dslug not in driverStats:
        driverStats[dslug] = {'bySeason': {}, 'allTime': {'points': 0, 'wins': 0, 'podiums': 0}}
        created['driversAdded'].append(dslug)

# Ensure each driver has an entry for each season
for dslug in list(driverStats.keys()):
    d = driverStats[dslug]
    bySeason = d.setdefault('bySeason', {})
    for s in seasons:
        key = str(s)
        if key not in bySeason:
            team_guess = guess_team_name_for(s, dslug, entry_map.get(dslug, {}).get('teamSlug'))
            bySeason[key] = {'team': team_guess or '', 'points': 0, 'wins': 0, 'podiums': 0, 'poles': 0, 'position': None}
            created['driverSeasonsAdded'].append({'driver': dslug, 'season': key})
        else:
            # fill common missing fields inside season object
            sd = bySeason[key]
            if 'points' not in sd: sd['points'] = 0
            if 'wins' not in sd: sd['wins'] = 0
            if 'podiums' not in sd: sd['podiums'] = 0
            if 'poles' not in sd: sd['poles'] = 0
            if 'position' not in sd: sd['position'] = None
            if 'team' not in sd or sd.get('team') is None:
                sd['team'] = guess_team_name_for(s, dslug, entry_map.get(dslug, {}).get('teamSlug')) or ''

# Ensure each team has season entries
for team in entries.get('teams', []):
    tslug = team.get('slug') or normalize(team.get('name'))
    tstats = teamStats.setdefault(tslug, {})
    bySeason = tstats.setdefault('bySeason', {})
    for s in seasons:
        key = str(s)
        if key not in bySeason:
            bySeason[key] = {'points': 0, 'wins': 0}
            created['teamsSeasonsAdded'].append({'team': tslug, 'season': key})

# backup and write updated stats
stats_path.replace(backup_path)
out_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding='utf8')

print('Backup written to', backup_path)
print('Updated stats written to', out_path)
print('Summary of created items:')
print(json.dumps(created, indent=2))
