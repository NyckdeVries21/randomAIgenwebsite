#!/usr/bin/env python3
import json
import time
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parent.parent
out_path = root / 'data' / 'stats.json'
backup_path = root / 'data' / 'stats.json.bak.full'

def fetch_json(url):
    with urlopen(url) as r:
        return json.load(r)

def slugify(name):
    return ''.join(c.lower() if c.isalnum() else '-' for c in (name or '')).strip('-')

seasons = list(range(2020, 2027))

driver_stats = {}
team_stats = {}

for s in seasons:
    print('Season', s)
    # fetch driver standings to get season points and constructor mapping
    url_ds = f'https://ergast.com/api/f1/{s}/driverStandings.json'
    ds = fetch_json(url_ds)
    lists = ds.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
    driver_constructor_map = {}
    if lists:
        for d in lists[0].get('DriverStandings', []):
            driver = d.get('Driver', {})
            name = (driver.get('givenName','') + ' ' + driver.get('familyName','')).strip()
            dslug = slugify(name)
            constructor = d.get('Constructors', [])
            teamName = constructor[0].get('name') if constructor else ''
            driver_constructor_map[dslug] = teamName

    # fetch list of races for season
    races_url = f'https://ergast.com/api/f1/{s}.json?limit=1000'
    races_data = fetch_json(races_url)
    races = races_data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
    for race in races:
        roundnum = race.get('round')
        print('  Race', roundnum, race.get('raceName'))
        # fetch results
        res_url = f'https://ergast.com/api/f1/{s}/{roundnum}/results.json'
        res_data = fetch_json(res_url)
        results = res_data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
        if not results: continue
        race_results = results[0].get('Results', [])
        # count poles via qualifying
        qual_url = f'https://ergast.com/api/f1/{s}/{roundnum}/qualifying.json'
        qual = fetch_json(qual_url)
        qual_races = qual.get('MRData', {}).get('RaceTable', {}).get('Races', [])
        poles = set()
        if qual_races:
            for qres in qual_races[0].get('QualifyingResults', []):
                if qres.get('position') == '1':
                    qdriver = qres.get('Driver', {})
                    qname = (qdriver.get('givenName','') + ' ' + qdriver.get('familyName','')).strip()
                    poles.add(slugify(qname))

        for r in race_results:
            driver = r.get('Driver', {})
            name = (driver.get('givenName','') + ' ' + driver.get('familyName','')).strip()
            dslug = slugify(name)
            constructor = r.get('Constructor', {})
            teamName = constructor.get('name','')
            pos = int(r.get('position', '0')) if r.get('position') and r.get('position').isdigit() else None
            points = int(float(r.get('points','0')))
            # fastest lap detection
            fastest = 0
            fl = r.get('FastestLap')
            if fl:
                # Ergast includes rank for fastest lap
                try:
                    if int(fl.get('rank','0')) == 1:
                        fastest = 1
                except:
                    fastest = 0

            # init driver entry
            ds = driver_stats.setdefault(dslug, {'bySeason': {}, 'allTime': {'points':0,'wins':0,'podiums':0,'poles':0,'fastestLaps':0}})
            bys = ds['bySeason'].setdefault(str(s), {'team': '', 'points':0,'wins':0,'podiums':0,'poles':0,'position':None,'fastestLaps':0})
            # set team name if not present
            if not bys.get('team'):
                bys['team'] = teamName or driver_constructor_map.get(dslug,'')
            # aggregate
            bys['points'] = bys.get('points',0) + points
            if pos == 1:
                bys['wins'] = bys.get('wins',0) + 1
                ds['allTime']['wins'] = ds['allTime'].get('wins',0) + 1
            if pos and pos <= 3:
                bys['podiums'] = bys.get('podiums',0) + 1
                ds['allTime']['podiums'] = ds['allTime'].get('podiums',0) + 1
            if dslug in poles:
                bys['poles'] = bys.get('poles',0) + 1
                ds['allTime']['poles'] = ds['allTime'].get('poles',0) + 1
            if fastest:
                bys['fastestLaps'] = bys.get('fastestLaps',0) + 1
                ds['allTime']['fastestLaps'] = ds['allTime'].get('fastestLaps',0) + 1
            # position overwritten to last known finishing pos if present
            if pos is not None:
                bys['position'] = pos
            # accumulate season points to allTime (we'll sum at end to avoid double counting)
            ds['allTime']['points'] = ds['allTime'].get('points',0) + points

            # team aggregation per season
            tslug = slugify(teamName)
            ts = team_stats.setdefault(tslug, {'bySeason': {}, 'allTime': {'points':0,'wins':0}})
            tbs = ts['bySeason'].setdefault(str(s), {'points':0,'wins':0})
            tbs['points'] = tbs.get('points',0) + points
            if pos == 1:
                tbs['wins'] = tbs.get('wins',0) + 1
                ts['allTime']['wins'] = ts['allTime'].get('wins',0) + 1
            ts['allTime']['points'] = ts['allTime'].get('points',0) + points

        # polite pause to avoid hammering the API
        time.sleep(0.5)

# final cleanup: ensure seasons list and convert to desired structure
out = {'seasons': seasons, 'driverStats': {}, 'teamStats': {}}
for dslug, d in driver_stats.items():
    # ensure all seasons present
    bys = d.get('bySeason', {})
    for s in seasons:
        bys.setdefault(str(s), {'team': '', 'points':0,'wins':0,'podiums':0,'poles':0,'position':None,'fastestLaps':0})
    out['driverStats'][dslug] = {'bySeason': bys, 'allTime': d.get('allTime',{})}

for tslug, t in team_stats.items():
    bys = t.get('bySeason', {})
    for s in seasons:
        bys.setdefault(str(s), {'points':0,'wins':0})
    out['teamStats'][tslug] = {'bySeason': bys, 'allTime': t.get('allTime',{})}

# backup existing
if out_path.exists():
    out_path.replace(backup_path)
    print('Existing stats.json backed up to', backup_path)

out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf8')
print('Wrote full stats to', out_path)
