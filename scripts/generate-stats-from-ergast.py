#!/usr/bin/env python3
import json
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parent.parent
out_path = root / 'data' / 'stats.generated.json'
backup_path = root / 'data' / 'stats.json.bak.ergast'

seasons = list(range(2020, 2027))

def fetch(url):
    with urlopen(url) as r:
        return json.load(r)

driver_stats = {}
team_stats = {}

for s in seasons:
    url = f'https://ergast.com/api/f1/{s}/driverStandings.json'
    print('Fetching', url)
    data = fetch(url)
    standings = data.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
    if not standings:
        print('No standings for', s)
        continue
    drivers = standings[0].get('DriverStandings', [])
    for d in drivers:
        driver = d.get('Driver', {})
        family = driver.get('familyName', '')
        given = driver.get('givenName','')
        name = f"{given} {family}".strip()
        slug = '-'.join(name.lower().replace('ú','u').replace('ö','o').replace('í','i').split())
        points = int(float(d.get('points', '0')))
        wins = int(d.get('wins', '0'))
        position = int(d.get('position', '0'))
        constructors = d.get('Constructors', [])
        teamName = constructors[0].get('name') if constructors else ''
        ds = driver_stats.setdefault(slug, {'bySeason': {}, 'allTime': {'points':0,'wins':0,'podiums':0}})
        ds['bySeason'][str(s)] = {'team': teamName, 'points': points, 'wins': wins, 'podiums': 0, 'poles': 0, 'position': position}
        # accumulate allTime points/wins
        at = ds.setdefault('allTime', {'points':0,'wins':0,'podiums':0})
        at['points'] = at.get('points',0) + points
        at['wins'] = at.get('wins',0) + wins

    # constructor standings for teams
    turl = f'https://ergast.com/api/f1/{s}/constructorStandings.json'
    print('Fetching', turl)
    tdata = fetch(turl)
    tlist = tdata.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
    if tlist:
        cons = tlist[0].get('ConstructorStandings', [])
        for c in cons:
            cname = c.get('Constructor', {}).get('name','')
            cslug = '-'.join(cname.lower().split())
            pts = int(float(c.get('points','0')))
            wins = int(c.get('wins','0'))
            ts = team_stats.setdefault(cslug, {'bySeason': {}, 'allTime': {'points':0,'wins':0}})
            ts['bySeason'][str(s)] = {'points': pts, 'wins': wins}
            at = ts.setdefault('allTime', {'points':0,'wins':0})
            at['points'] = at.get('points',0) + pts
            at['wins'] = at.get('wins',0) + wins

# ensure seasons array
out = {'seasons': seasons, 'driverStats': driver_stats, 'teamStats': team_stats}

if (root / 'data' / 'stats.json').exists():
    (root / 'data' / 'stats.json').replace(backup_path)
    print('Backed up existing stats.json to', backup_path)

out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf8')
print('Wrote generated stats to', out_path)
