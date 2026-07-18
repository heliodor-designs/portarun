"""Fetch raw data from all sources into pipeline/raw/.

Usage:  python3 -m pipeline.fetch [--only SOURCE]

Requires network access to arcgis.com and overpass-api.de — run this locally,
then `python3 -m pipeline.normalize` to build web/data/potties.geojson.
Stdlib only: no pip installs needed.
"""

import argparse
import json
import pathlib
import sys
import urllib.parse
import urllib.request

from .sources import greensboro_parks, greensboro_permits, osm_toilets

SOURCES = [greensboro_permits, greensboro_parks, osm_toilets]
RAW_DIR = pathlib.Path(__file__).parent / "raw"
USER_AGENT = "portarun-pipeline/0.1"


def get_json(url, data=None, timeout=90):
    """GET (or POST when data is given) a URL and decode the JSON response."""
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=[s.NAME for s in SOURCES])
    args = parser.parse_args(argv)

    RAW_DIR.mkdir(exist_ok=True)
    failures = 0
    for source in SOURCES:
        if args.only and source.NAME != args.only:
            continue
        print(f"fetching {source.NAME} ...", flush=True)
        try:
            raw = source.fetch(get_json)
        except Exception as exc:  # keep going: one bad source shouldn't kill the run
            print(f"  FAILED: {exc}", file=sys.stderr)
            failures += 1
            continue
        path = RAW_DIR / f"{source.NAME}.json"
        path.write_text(json.dumps(raw, indent=1))
        count = len(raw.get("features", raw.get("elements", [])))
        print(f"  ok: {count} records -> {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
