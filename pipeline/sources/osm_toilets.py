"""OpenStreetMap amenity=toilets in the Greensboro area, via the Overpass API.

Community-mapped public toilets: instant baseline coverage (~4M mapped
worldwide). Treated as verified restrooms at slightly lower confidence than
the city's own parks data.
"""

import datetime

NAME = "osm_toilets"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Greensboro bounding box: (south, west, north, east)
BBOX = (35.95, -80.05, 36.20, -79.60)

QUERY = f"""
[out:json][timeout:60];
(
  node["amenity"="toilets"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["amenity"="toilets"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out center tags;
"""


def fetch(get_json):
    payload = get_json(OVERPASS_URL, data={"data": QUERY})
    return {
        "source": NAME,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elements": payload.get("elements", []),
    }


def parse(raw, now=None):
    out = []
    for el in raw.get("elements", []):
        tags = el.get("tags", {})
        if tags.get("access") in ("private", "no"):
            continue
        if el.get("type") == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:  # ways/relations come back with a computed center
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue
        detail_bits = [
            f"access: {tags['access']}" if tags.get("access") else "",
            f"fee: {tags['fee']}" if tags.get("fee") else "",
            f"hours: {tags['opening_hours']}" if tags.get("opening_hours") else "",
            "wheelchair accessible" if tags.get("wheelchair") == "yes" else "",
        ]
        out.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": f"osm:{el.get('type')}/{el.get('id')}",
                    "source": "osm",
                    "kind": "restroom",
                    "confidence": 0.75 if tags.get("access") == "yes" else 0.7,
                    "name": tags.get("name") or "Public toilet (OSM)",
                    "detail": " · ".join(b for b in detail_bits if b)
                    or "Mapped on OpenStreetMap",
                    "fetched_at": raw.get("fetched_at"),
                },
            }
        )
    return out
