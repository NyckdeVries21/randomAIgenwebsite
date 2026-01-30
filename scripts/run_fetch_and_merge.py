#!/usr/bin/env python3
"""Orchestrator: run Wikipedia + Ergast fetchers, then fix and validate, producing a merged `data/stats.json`.

Usage:
  python scripts/run_fetch_and_merge.py

This script runs the other scripts (which perform network requests) and merges their outputs.
Run locally (requires internet and Python packages in requirements.txt).
"""
import subprocess
import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
WIKI_OUT = DATA / 'stats.wikipedia.json'
ERGAST_OUT = DATA / 'stats.generated.json'
FIXED_OUT = DATA / 'stats.fixed.json'
FINAL = DATA / 'stats.json'

def run(cmd):
    print('RUN:', ' '.join(cmd))
    r = subprocess.run(cmd, shell=False)
    if r.returncode != 0:
        raise SystemExit(f'Command failed: {cmd}')

def merge_and_write():
    # If fixed exists, use it as final; otherwise try generated
    if FIXED_OUT.exists():
        print('Using', FIXED_OUT)
        src = json.loads(FIXED_OUT.read_text(encoding='utf8'))
        FINAL.write_text(json.dumps(src, indent=2, ensure_ascii=False), encoding='utf8')
        print('Wrote', FINAL)
        return

    # fallback: try to merge Ergast + Wikipedia into stats.json (best-effort)
    out = {}
    if ERGAST_OUT.exists():
        out = json.loads(ERGAST_OUT.read_text(encoding='utf8'))
    else:
        print('No', ERGAST_OUT, 'found')

    # attach wikipedia career totals if available
    if WIKI_OUT.exists():
        wiki = json.loads(WIKI_OUT.read_text(encoding='utf8'))
        # attach under driverStats -> for each driver slug, set 'careerFromWiki'
        ds = out.setdefault('driverStats', {})
        for slug, data in wiki.items():
            d = ds.setdefault(slug, {})
            d['careerFromWiki'] = data

    if out:
        FINAL.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf8')
        print('Wrote', FINAL)
    else:
        print('No generated data to write')

def main():
    # run generators (Ergast only — Wikipedia disabled per user request)
    try:
        run([sys.executable, 'scripts/fetch_stats_ergast.py'])
    except SystemExit as e:
        print('Ergast fetch failed:', e)

    # run fixer
    try:
        run([sys.executable, 'scripts/fix_stats.py'])
    except SystemExit as e:
        print('Fixer failed:', e)

    # run validator
    try:
        run([sys.executable, 'scripts/validate-stats.py'])
    except SystemExit as e:
        print('Validator failed:', e)

    # merge/choose final file
    merge_and_write()

    # compute championships/titles based on careerSummary (if present)
    try:
        run([sys.executable, 'scripts/compute_championships.py'])
    except SystemExit as e:
        print('Compute championships failed:', e)

if __name__ == '__main__':
    main()
