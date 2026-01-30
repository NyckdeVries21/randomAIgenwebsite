#!/usr/bin/env python3
"""Fetch junior (F2/F3) career info for drivers who debuted in F1 in 2025 or later.

This script reads `data/stats.generated.json` (or `data/stats.json`) to get the
driver list collected by `fetch_stats_ergast.py`, identifies drivers whose first
F1 season is 2025 or later, then queries the English Wikipedia API for each
driver page and searches the wikitext for mentions of Formula 2 / Formula 3 and
nearby years. Results are written to `data/drivers.junior.json` and merged into
`data/stats.generated.json` (if present).

This is a best-effort extractor — Wikipedia pages differ markedly, so the
script looks for nearby 4-digit years around occurrences of "Formula 2"/"F2"
and "Formula 3"/"F3" and returns the found years.

Requires: requests
"""
from pathlib import Path
import json
import re
import time
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
STATS_GEN = DATA / 'stats.generated.json'
STATS_SRC = DATA / 'stats.json'
OUT_FILE = DATA / 'drivers.junior.json'

WIKI_API = 'https://en.wikipedia.org/w/api.php'

def load_stats():
    if STATS_GEN.exists():
        return json.loads(STATS_GEN.read_text(encoding='utf8'))
    if STATS_SRC.exists():
        return json.loads(STATS_SRC.read_text(encoding='utf8'))
    raise SystemExit('No stats file found (data/stats.generated.json or data/stats.json)')

def extract_title_from_url(url):
    try:
        if '/wiki/' in url:
            title = url.split('/wiki/',1)[1]
            return unquote(title)
    except Exception:
        pass
    return None

def wiki_search(title):
    params = {'action':'query','list':'search','srsearch':title,'format':'json','srlimit':1}
    r = requests.get(WIKI_API, params=params, timeout=15)
    r.raise_for_status()
    js = r.json()
    hits = js.get('query',{}).get('search', [])
    if not hits:
        return None
    return hits[0].get('title')

def fetch_wikitext(title):
    params = {'action':'query','prop':'revisions','rvprop':'content','rvslots':'*','titles':title,'format':'json'}
    r = requests.get(WIKI_API, params=params, timeout=15)
    r.raise_for_status()
    js = r.json()
    pages = js.get('query', {}).get('pages', {})
    for p in pages.values():
        revs = p.get('revisions')
        if revs:
            # wikitext is in slots->main->* (newer MediaWiki)
            slot = revs[0].get('slots', {}).get('main', {})
            content = slot.get('*') if isinstance(slot, dict) else revs[0].get('*')
            return content or ''
    return ''

def fetch_parsed_html(title):
    params = {'action':'parse','page':title,'prop':'text','format':'json'}
    r = requests.get(WIKI_API, params=params, timeout=15)
    r.raise_for_status()
    js = r.json()
    text = js.get('parse', {}).get('text', {}).get('*', '')
    return text

def find_series_years_from_tables(html, keywords):
    found = set()
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    # examine captions and entire table text
    tables = soup.find_all('table')
    pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
    for tbl in tables:
        txt = ''
        cap = tbl.find('caption')
        if cap and cap.get_text(strip=True):
            txt += cap.get_text(separator=' ') + '\n'
        # include nearby heading (previous siblings that are headers)
        prev = tbl.find_previous_sibling()
        for _ in range(3):
            if not prev:
                break
            if prev.name and prev.name.startswith('h'):
                txt += prev.get_text(separator=' ') + '\n'
                break
            prev = prev.find_previous_sibling()
        txt += tbl.get_text(separator=' ')
        for kw in keywords:
            if re.search(re.escape(kw), txt, flags=re.IGNORECASE):
                for y in pattern.findall(txt):
                    y_int = int(y)
                    if 1990 <= y_int <= 2035:
                        found.add(y_int)
                # also try to detect header rows with years like '2019 2020 2021'
    return sorted(found)

def find_series_years(wikitext, keywords):
    # find occurrences of keywords and search +/- 200 chars for 4-digit years
    found = set()
    pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
    for kw in keywords:
        for m in re.finditer(re.escape(kw), wikitext, flags=re.IGNORECASE):
            start = max(0, m.start() - 200)
            end = min(len(wikitext), m.end() + 200)
            snippet = wikitext[start:end]
            for y in pattern.findall(snippet):
                y_int = int(y)
                if 1990 <= y_int <= 2035:
                    found.add(y_int)
    # sort and return
    return sorted(found)

def main():
    stats = load_stats()
    drivers = stats.get('drivers', {})
    results = {}

    targets = []
    for slug, entry in drivers.items():
        seasons = entry.get('seasons', [])
        if not seasons:
            continue
        # convert seasons to ints and take earliest
        try:
            yrs = sorted(int(s) for s in seasons)
        except Exception:
            continue
        debut = yrs[0]
        if debut >= 2025:
            targets.append((slug, entry, debut))

    print(f'Found {len(targets)} drivers with debut >= 2025 to inspect')

    for i, (slug, entry, debut) in enumerate(targets, start=1):
        print(f'[{i}/{len(targets)}] Processing', slug)
        title = None
        url = entry.get('url')
        if url:
            title = extract_title_from_url(url)
        if not title:
            name = ' '.join(filter(None, [entry.get('givenName'), entry.get('familyName')]))
            title = wiki_search(name)
        if not title:
            print('  No Wikipedia title found for', slug)
            continue
        time.sleep(0.3)
        try:
            wikitext = fetch_wikitext(title)
        except Exception as e:
            print('  Failed fetching wikitext for', title, e)
            wikitext = ''

        # best-effort: use both wikitext search and parsed HTML table extraction
        f2_years = find_series_years(wikitext, ['Formula 2', 'FIA Formula 2 Championship', 'F2'])
        f3_years = find_series_years(wikitext, ['Formula 3', 'FIA Formula 3 Championship', 'F3'])

        # try parsing tables for stronger signals
        try:
            html = fetch_parsed_html(title)
            table_f2 = find_series_years_from_tables(html, ['Formula 2', 'F2', 'FIA Formula 2'])
            table_f3 = find_series_years_from_tables(html, ['Formula 3', 'F3', 'FIA Formula 3'])
        except Exception:
            table_f2 = []
            table_f3 = []

        # merge unique
        f2_years = sorted(set(f2_years) | set(table_f2))
        f3_years = sorted(set(f3_years) | set(table_f3))

        results[slug] = {
            'wikipedia_title': title,
            'wikipedia_url': f'https://en.wikipedia.org/wiki/{title.replace(" ","_")}',
            'debut': debut,
            'F2_years': f2_years,
            'F3_years': f3_years,
        }
        # attach to original drivers structure for convenience
        drivers[slug]['juniorCareer'] = {'F2_years': f2_years, 'F3_years': f3_years, 'wikipedia_title': title}
        # be polite to Wikipedia
        time.sleep(0.5)

    # write outputs
    OUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf8')
    print('Wrote', OUT_FILE)

    # if stats.generated exists, overwrite with updated drivers attached
    if STATS_GEN.exists():
        stats['drivers'] = drivers
        STATS_GEN.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding='utf8')
        print('Updated', STATS_GEN)

if __name__ == '__main__':
    main()
