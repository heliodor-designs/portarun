"""Merge raw source data into web/data/potties.geojson.

Usage:  python3 -m pipeline.normalize

Reads pipeline/raw/<source>.json if present (real data from `fetch`), falling
back to pipeline/fixtures/<source>.json with a warning so the pipeline and map
work offline.

Output feature properties: id, source (permit|parks|osm), kind
(restroom|porta_potty_likely), confidence (0-1), name, detail, fetched_at.
A future crowdsourcing milestone appends reports[] without breaking this schema.
"""

import datetime
import json
import math
import pathlib
import sys

from .sources import greensboro_parks, greensboro_permits, osm_toilets

SOURCES = [greensboro_permits, greensboro_parks, osm_toilets]
PIPELINE_DIR = pathlib.Path(__file__).parent
# Emit into web/ so the whole app (map + data) is one self-contained, deployable
# directory with base-path-independent relative URLs.
OUT_PATH = PIPELINE_DIR.parent / "web" / "data" / "potties.geojson"

DEDUPE_RADIUS_M = 30


def haversine_m(lon1, lat1, lon2, lat2):
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def dedupe(features, radius_m=DEDUPE_RADIUS_M):
    """Drop lower-confidence features within radius_m of a kept one of the same kind.

    Different kinds never merge — an OSM restroom next to a construction site is
    two distinct pins.
    """
    kept = []
    for feat in sorted(
        features, key=lambda f: f["properties"]["confidence"], reverse=True
    ):
        lon, lat = feat["geometry"]["coordinates"]
        kind = feat["properties"]["kind"]
        if any(
            k["properties"]["kind"] == kind
            and haversine_m(lon, lat, *k["geometry"]["coordinates"]) <= radius_m
            for k in kept
        ):
            continue
        kept.append(feat)
    return kept


def load_raw(source, raw_dir=None, fixtures_dir=None):
    raw_dir = raw_dir or PIPELINE_DIR / "raw"
    fixtures_dir = fixtures_dir or PIPELINE_DIR / "fixtures"
    real = raw_dir / f"{source.NAME}.json"
    if real.exists():
        return json.loads(real.read_text()), False
    fixture = fixtures_dir / f"{source.NAME}.json"
    return json.loads(fixture.read_text()), True


def build_collection(features_by_source, generated_at=None):
    features = dedupe([f for feats in features_by_source.values() for f in feats])
    features.sort(key=lambda f: f["properties"]["id"])  # stable diffs
    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated_at": (
                generated_at
                or datetime.datetime.now(datetime.timezone.utc).isoformat()
            ),
            "counts": {name: len(feats) for name, feats in features_by_source.items()},
            "total_after_dedupe": len(features),
        },
        "features": features,
    }


def main(argv=None):
    features_by_source = {}
    used_fixtures = []
    for source in SOURCES:
        raw, is_fixture = load_raw(source)
        if is_fixture:
            used_fixtures.append(source.NAME)
        features_by_source[source.NAME] = source.parse(raw)

    if used_fixtures:
        print(
            f"WARNING: no raw data for {', '.join(used_fixtures)}; using fixtures. "
            "Run `uv run potties-fetch` (or `make fetch`) with network access "
            "for real data.",
            file=sys.stderr,
        )

    collection = build_collection(features_by_source)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(collection, indent=1))
    print(
        f"wrote {OUT_PATH} — {collection['metadata']['total_after_dedupe']} features "
        f"({collection['metadata']['counts']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
