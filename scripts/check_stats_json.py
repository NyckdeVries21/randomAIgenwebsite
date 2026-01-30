#!/usr/bin/env python3
"""Simple JSON validator for data/stats.json

Run locally to get precise parse error location:

python scripts/check_stats_json.py

"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'data' / 'stats.json'

def main():
    try:
        text = TARGET.read_text(encoding='utf-8')
    except Exception as e:
        print('Error reading', TARGET, e)
        sys.exit(2)

    try:
        json.loads(text)
        print('OK: valid JSON')
        return 0
    except json.JSONDecodeError as e:
        print('JSONDecodeError:')
        print('  msg:', e.msg)
        print('  pos:', e.pos)
        print('  lineno:', e.lineno)
        print('  colno:', e.colno)
        # show context lines
        lines = text.splitlines()
        ln = max(0, e.lineno - 3)
        for i in range(ln, min(len(lines), e.lineno + 2)):
            mark = '->' if (i + 1) == e.lineno else '  '
            print(f"{mark} {i+1:4}: {lines[i]}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
