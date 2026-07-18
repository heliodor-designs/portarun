# PortaRun

A mobile-first web app that shows runners where the nearest restroom or
porta-potty is. Proof of concept: **Greensboro, NC**.

## What it is

An interactive map with two kinds of pins:

- **Restrooms** — verified permanent public toilets (city parks and greenways,
  plus community-mapped toilets from OpenStreetMap).
- **Likely porta-potties** — inferred from active building permits and clearly
  marked *unverified*, each with a confidence score. OSHA (29 CFR 1926.51)
  requires toilets on active construction sites, so an active permit is a
  strong predictor of a porta-potty at that address.

It's a progressive web app: installable to your home screen, and the last-loaded
map keeps working offline.

## How it works

Three data sources are fetched, normalized to a common schema, merged, and
deduplicated into a single GeoJSON file the map loads:

| Source | Layer | Confidence |
| --- | --- | --- |
| City park & greenway restrooms | Greensboro ArcGIS `PiedmontDiscovery` Park Facilities (`Facility_Type = 'Restroom'`) | 0.9 |
| OpenStreetMap toilets | `amenity=toilets` via the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) | ~0.7 |
| Building permits | Greensboro ArcGIS `BuildingPermits` points | 0.05–0.8 |

```
pipeline/fetch.py          pull each source's raw JSON -> pipeline/raw/
pipeline/sources/*.py      one module per source: fetch() + parse() -> features
pipeline/normalize.py      merge, confidence-score, dedupe (30 m, same kind)
                           -> web/data/potties.geojson
web/                       Leaflet map, PWA manifest, service worker, icons
```

Each feature carries: `id`, `source` (`permit|parks|osm`), `kind`
(`restroom|porta_potty_likely`), `confidence` (0–1), `name`, `detail`, and
`fetched_at`.

**Porta-potty confidence.** A permit is included only if it's active/issued and
was issued within the last 30 days (`MAX_AGE_DAYS` in
`pipeline/sources/greensboro_permits.py`). Score starts at 0.3 and adjusts for
the type of work: new construction, commercial/industrial or multi-family, and
high project value raise it; trade-only work (an electrical or mechanical permit
with no general construction) lowers it. A plumbing renovation gets a small
boost, since it takes the building's own toilets out of service. Scores are
clamped to 0.05–0.9.

## Build & run

### With [uv](https://docs.astral.sh/uv/) (recommended, works on Windows)

uv downloads Python automatically if you don't have it. From the repo folder:

```sh
uv run potties-fetch                  # pull live data (needs internet)
uv run potties-build                  # build web/data/potties.geojson
uv run python -m http.server 8000     # serve the map
uv run python -m unittest discover -s pipeline/tests -t . -v   # tests
```

Then open <http://localhost:8000/web/> on your phone or laptop.

### With plain Python 3 (no installs)

The pipeline is standard-library only. Use `python` on Windows, `python3` on
Mac/Linux:

```sh
python -m pipeline.fetch              # or: make fetch
python -m pipeline.normalize          # or: make build
python -m http.server 8000            # or: make serve
python -m unittest discover -s pipeline/tests -t . -v    # or: make test
```

Committed sample data ships with the repo, so `potties-build` and the map work
out of the box before you run a live fetch.

### Install on your phone

Open the served URL over HTTPS (or `localhost`) in a phone browser, then use
**Share → Add to Home Screen** (iOS Safari) or the **Install** prompt (Android
Chrome). Regenerate the app icons with `python web/make_icons.py`.

## Deploy (GitHub Pages)

The whole app lives under `web/` with relative URLs, so that directory is the
deployable site root. `.github/workflows/deploy.yml` rebuilds the data and
publishes it as a Pages artifact on push, on manual dispatch, and **daily at
08:00 UTC**. Data is built fresh in CI (never committed); if a fetch comes back
degraded the run fails and the last good deployment stays live.

To go live:

1. Push the repo to GitHub.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. Trigger the workflow (push, or **Actions → Build data & deploy → Run
   workflow**). The site URL appears at Settings → Pages once it succeeds.

HTTPS is automatic. For a custom domain, add a `web/CNAME` file and point DNS at
GitHub Pages — no code changes needed.

## Roadmap

- Crowdsourcing: report missing or wrong pins, with freshness decay
- More layers: special-event permits (races), runner-friendly businesses
- Expand beyond Greensboro
