# Run instructions — stats fetching & site

This project uses the Ergast API (no Wikipedia) to fetch F1 season data and populate `data/`.

Quick steps (Windows PowerShell, run from repo root):

```powershell
# install Python deps
python -m pip install -r requirements.txt

# run orchestrator: fetch Ergast (2000..current), fix, validate, compute championships
python scripts/run_fetch_and_merge.py

# (optional) serve the site locally and open in browser
# python -m http.server 8000
```

Notes
- The orchestrator now only uses the Ergast API for F1 historical + per-season data.
- `scripts/fetch_stats_ergast.py` defaults to seasons 2000..<current year> and normalizes Ergast ids to site slugs (underscores -> hyphens).
- `scripts/fix_stats.py` fills missing seasons and writes `data/stats.fixed.json`.
- `scripts/validate-stats.py` writes `data/stats-validation-report.json` with missing-field diagnostics.
- `scripts/compute_championships.py` derives `allTime.championships` from `careerSummary` entries.

Debugging
- If the page shows "Kon statistieken niet laden":
  - Make sure you serve the site over HTTP (not file://).
  - Check `data/stats.json` or `data/stats.generated.json` for accessibility.
  - If you open `index.html` directly, the page will read data from the `data/` folder; use DevTools → Network to inspect requests when necessary.
  - If Python is not installed, install from https://python.org and retry the commands above.

APIs
- Ergast API (recommended): https://ergast.com/mrd/ — free access to race results, standings and qualifying per season.
- For deeper telemetry, consider `fastf1` (Python) or commercial providers if you need richer datasets.

If you want, I can also add a `--years` flag to the Ergast fetcher or produce a single consolidated `data/stats.json` artifact for deployment.
