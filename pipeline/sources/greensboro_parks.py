"""Greensboro park / greenway restrooms -> verified permanent restroom locations.

These are public, permanent, and sit exactly where runners are (the greenway
network), so they form the high-confidence foundation layer.

The city models amenities as individual points in a "Park Facilities" layer
(ParksRec/PiedmontDiscovery_MS, layer 0), not as a yes/no flag on a park
polygon. Each facility carries a Facility_Type; we keep the rows where that is
"Restroom". Facility_Name is the *park's* name, and each row has its own
coordinates, so one park with two restroom buildings yields two points.
"""

import datetime

from . import arcgis

NAME = "greensboro_parks"

LAYER_URL = (
    "https://gis.greensboro-nc.gov/arcgis/rest/services/"
    "ParksRec/PiedmontDiscovery_MS/MapServer/0"
)

FIELD_MAP = {
    "facility_id": "Facility_ID",  # unique per facility; a park can have several
    "facility_type": "Facility_Type",
    "park_name": "Facility_Name",  # e.g. "Lake Daniel Park" (the containing park)
    "address": "Address",
    "description": "Description",
    "status": "Status",  # Open / Open Fee / Open Restricted / Closed / None
}

RESTROOM_TYPE = "restroom"


def fetch(get_json):
    meta = get_json(f"{LAYER_URL}?f=json")
    arcgis.check_fields(meta, FIELD_MAP, NAME)
    where = f"{FIELD_MAP['facility_type']} = 'Restroom'"
    features = arcgis.fetch_all(get_json, LAYER_URL, where)
    return {
        "source": NAME,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "layer_url": LAYER_URL,
        "features": features,
    }


def parse(raw, now=None):
    f = FIELD_MAP
    out = []
    for feature in raw.get("features", []):
        coords = arcgis.point_coords(feature)
        if coords is None:
            continue
        props = feature.get("properties", {})
        if (props.get(f["facility_type"]) or "").strip().lower() != RESTROOM_TYPE:
            continue
        if "closed" in (props.get(f["status"]) or "").strip().lower():
            continue
        park = (props.get(f["park_name"]) or "City park").strip()
        # A park can hold several restroom buildings, so key on the unique
        # facility id (falling back to the slug) to keep them distinct.
        slug = park.lower().replace(" ", "-")
        fid = props.get(f["facility_id"])
        feature_id = f"parks:{slug}-{fid}" if fid is not None else f"parks:{slug}"
        detail = props.get(f["description"]) or props.get(f["address"]) \
            or "City park restroom"
        out.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [coords[0], coords[1]]},
                "properties": {
                    "id": feature_id,
                    "source": "parks",
                    "kind": "restroom",
                    "confidence": 0.9,
                    "name": f"{park} restroom",
                    "detail": detail,
                    "fetched_at": raw.get("fetched_at"),
                },
            }
        )
    return out
