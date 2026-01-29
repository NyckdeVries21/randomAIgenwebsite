import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
entries_path = root / 'data' / 'entries-2026.json'
stats_path = root / 'data' / 'stats.json'
out_path = root / 'data' / 'stats-validation-report.json'

def slugify(name):
    return ''.join(c.lower() if c.isalnum() else '-' for c in (name or '')).strip('-')

def load(p):
    try:
        return json.loads(p.read_text(encoding='utf8'))
    except Exception as e:
        print('Failed to read', p, e)
        raise

entries = load(entries_path)
stats = load(stats_path)

report = {'missingInStats':[], 'missingInEntries':[], 'driversWithMissingFields':[], 'summary':{'entriesDrivers':0,'statsDrivers':0}}

entry_drivers = []
for team in entries.get('teams',[]):
    for d in team.get('drivers',[]):
        s = d.get('slug') or slugify(d.get('name'))
        t = team.get('slug') or slugify(team.get('name'))
        entry_drivers.append({'name': d.get('name'), 'slug': s, 'team': t})

report['summary']['entriesDrivers'] = len(entry_drivers)

stats_drivers = list((stats.get('driverStats') or {}).keys())
report['summary']['statsDrivers'] = len(stats_drivers)

for ed in entry_drivers:
    if ed['slug'] not in (stats.get('driverStats') or {}):
        report['missingInStats'].append(ed)

for sd in stats_drivers:
    if not any(ed['slug'] == sd for ed in entry_drivers):
        report['missingInEntries'].append({'slug': sd})

fields_to_check = ['allTime','bySeason']
for slug, d in (stats.get('driverStats') or {}).items():
    missing = [f for f in fields_to_check if f not in d]
    seasons_missing = []
    bySeason = d.get('bySeason') or {}
    for s, sd in bySeason.items():
        miss = []
        if sd.get('points') is None:
            miss.append('points')
        if sd.get('team') is None:
            miss.append('team')
        if miss:
            seasons_missing.append({'season': s, 'missing': miss})
    if missing or seasons_missing:
        report['driversWithMissingFields'].append({'slug': slug, 'missing': missing, 'seasonsMissing': seasons_missing})

out_path.write_text(json.dumps(report, indent=2), encoding='utf8')
print('Validation complete. Report written to', out_path)
