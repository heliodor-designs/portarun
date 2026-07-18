"""Shared helpers for querying ArcGIS FeatureServer layers (Greensboro Open Gate City)."""

import datetime
import urllib.parse

PAGE_SIZE = 2000


class FieldMapError(RuntimeError):
    """Raised when a layer's live schema doesn't match our assumed field names."""


def check_fields(layer_meta, field_map, layer_name):
    """Verify every field we rely on exists in the live layer metadata.

    The field names in each source's FIELD_MAP are assumptions made offline;
    this fails loudly with the layer's real field list so they're easy to fix
    after the first live fetch.
    """
    actual = {f["name"] for f in layer_meta.get("fields", [])}
    missing = [v for v in field_map.values() if v not in actual]
    if missing:
        raise FieldMapError(
            f"Layer '{layer_name}' is missing expected fields {missing}.\n"
            f"Update FIELD_MAP in the source module. Actual fields:\n  "
            + "\n  ".join(sorted(actual))
        )


def query_url(layer_url, where, out_fields="*", offset=0):
    params = {
        "where": where,
        "outFields": out_fields,
        "f": "geojson",
        "outSR": "4326",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE_SIZE),
    }
    return f"{layer_url}/query?{urllib.parse.urlencode(params)}"


def fetch_all(get_json, layer_url, where, out_fields="*"):
    """Page through a FeatureServer query and return the combined feature list."""
    features = []
    offset = 0
    while True:
        page = get_json(query_url(layer_url, where, out_fields, offset))
        batch = page.get("features", [])
        features.extend(batch)
        if len(batch) < PAGE_SIZE:
            return features
        offset += PAGE_SIZE


def epoch_ms_to_date(value):
    """ArcGIS returns dates as epoch milliseconds; tolerate None/ISO strings."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.datetime.fromtimestamp(
            value / 1000, tz=datetime.timezone.utc
        ).date()
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def point_coords(feature):
    """Return (lon, lat) from a GeoJSON feature, or None if geometry is unusable."""
    geom = feature.get("geometry") or {}
    if geom.get("type") != "Point":
        return None
    coords = geom.get("coordinates") or []
    if len(coords) < 2 or coords[0] is None or coords[1] is None:
        return None
    return coords[0], coords[1]
