#!/usr/bin/env python3
"""Compute championships/titles from `careerSummary` and write into `data/stats.json`.

Usage: python scripts/compute_championships.py

This script looks for `careerSummary` entries per driver and counts seasons
where the `series` contains 'Formula One' and `position` is '1st'. It writes
`allTime.championships` field for each driver (0 if none).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / 'data' / 'stats.json'

def main():
    s = json.loads(STATS.read_text(encoding='utf8'))
    ds = s.setdefault('driverStats', {})
    updated = []
    for slug, info in ds.items():
        career = info.get('careerSummary') or []
        champs = 0
        for row in career:
            series = (row.get('series') or '').lower()
            pos = (row.get('position') or '').lower()
            if 'formula one' in series or series.strip().lower().startswith('formula one'):
                if pos and (pos == '1st' or pos.startswith('1')):
                    champs += 1
        at = info.setdefault('allTime', {})
        if at.get('championships') != champs:
            at['championships'] = champs
            updated.append(slug)

    if updated:
        STATS.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding='utf8')
        print('Updated championships for:', updated)
    else:
        print('No changes; championships already present or zero for all drivers')

if __name__ == '__main__':
    main()
