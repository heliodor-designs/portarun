"""Active Greensboro building permits -> "likely porta-potty" locations.

There is no porta-potty permit. The signal is indirect: OSHA 29 CFR 1926.51
requires toilets on active construction sites, so an active building permit is
a probabilistic predictor of a porta-potty at that address. Features from this
source are kind="porta_potty_likely" and never exceed 0.9 confidence.

Data: City of Greensboro "Building Inspections - Permits", served from the
city's own ArcGIS at gis.greensboro-nc.gov (Engineering & Inspections). Layer 6
("Building Permits Points - Main Dashboard") is one point per permit, 1998 to
present, with issue date, status, application type, cost breakdowns, and
residential/commercial/multi-family flags.

LAYER_URL and FIELD_MAP were verified against the live layer on the first real
fetch; arcgis.check_fields re-validates every field on each run.
"""

import datetime

from . import arcgis

NAME = "greensboro_permits"

LAYER_URL = (
    "https://gis.greensboro-nc.gov/arcgis/rest/services/"
    "EngineeringInspections/BuildingPermits_MS/MapServer/6"
)

# Logical name -> live ArcGIS field name.
FIELD_MAP = {
    "permit_number": "PermitNum",
    "status": "StatusCurrent",
    "application_type": "ApplicationType",  # New Construction, Addition, Repair, ...
    "comm_resid": "BP_COMM_RESID_MULT",     # C=commercial, I=industrial, R=residential
    "multi_family": "MultiFamily",          # Y / N / None
    "issued_date": "IssuedDate",
    "description": "Description",
    "address": "FullAddress",
    "value": "OfficalTotalCost",            # (sic) the layer spells it "Offical"
    "general_cost": "GeneralCost",
    "plumbing_cost": "PlumbingCost",
    "electrical_cost": "ElectricalCost",
    "mechanical_cost": "MechanicalCost",
}

# Statuses that mean construction is (or is about to be) underway. The live
# vocabulary is "Issued" / "Active" / "Final Inspection Made" (the last means
# the job is done, so it's excluded). Values arrive space-padded -> strip+lower.
ACTIVE_STATUSES = {"issued", "active", "in progress", "reissued"}

# Only permits issued within this window are considered "fresh" enough to still
# have a toilet on site. Kept short: a permit issued long ago is usually past
# the phase that needs a porta-potty (or the job is finished but never closed
# out), so we key on recency measured from the day the fetch runs.
MAX_AGE_DAYS = 30  # ~1 month


def _num(value):
    """ArcGIS cost fields are numeric but tolerate None/strings/blanks."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def fetch(get_json):
    """Pull layer metadata + recent active permits. Returns the raw payload to cache."""
    meta = get_json(f"{LAYER_URL}?f=json")
    arcgis.check_fields(meta, FIELD_MAP, NAME)
    cutoff = datetime.date.today() - datetime.timedelta(days=MAX_AGE_DAYS)
    status_field = FIELD_MAP["status"]
    where = (
        f"{FIELD_MAP['issued_date']} >= DATE '{cutoff.isoformat()}' "
        f"AND ({status_field} LIKE 'Issued%' OR {status_field} LIKE 'Active%')"
    )
    features = arcgis.fetch_all(get_json, LAYER_URL, where)
    return {
        "source": NAME,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "layer_url": LAYER_URL,
        "features": features,
    }


def confidence(status, application_type, comm_resid, multi_family, issued_date,
               value, general_cost, plumbing_cost, electrical_cost,
               mechanical_cost, now):
    """Score how likely an active porta-potty is on site, or None to exclude."""
    if (status or "").strip().lower() not in ACTIVE_STATUSES:
        return None
    if issued_date is None or (now - issued_date).days > MAX_AGE_DAYS:
        return None

    score = 0.3
    is_new = "new construction" in (application_type or "").lower()
    if is_new:
        score += 0.25
    if (comm_resid or "").strip().upper() in ("C", "I") or \
            (multi_family or "").strip().upper() == "Y":
        score += 0.15
    if _num(value) >= 500_000:
        score += 0.10

    plumbing, general = _num(plumbing_cost), _num(general_cost)
    electrical, mechanical = _num(electrical_cost), _num(mechanical_cost)
    # A plumbing renovation takes the building's own toilets out of service,
    # which *raises* the odds of a porta-potty on site.
    if not is_new and plumbing > 0:
        score += 0.05
    # Trade-only work (an HVAC swap, a panel upgrade) with no general
    # construction and no plumbing rarely warrants a site toilet.
    if not is_new and general == 0 and plumbing == 0 and \
            (electrical > 0 or mechanical > 0):
        score -= 0.15
    return round(min(max(score, 0.05), 0.9), 2)


def parse(raw, now=None):
    """Raw payload -> normalized GeoJSON features (see normalize.py schema)."""
    now = now or datetime.date.today()
    f = FIELD_MAP
    out = []
    for feature in raw.get("features", []):
        coords = arcgis.point_coords(feature)
        if coords is None:
            continue
        props = feature.get("properties", {})
        issued = arcgis.epoch_ms_to_date(props.get(f["issued_date"]))
        conf = confidence(
            props.get(f["status"]),
            props.get(f["application_type"]),
            props.get(f["comm_resid"]),
            props.get(f["multi_family"]),
            issued,
            props.get(f["value"]),
            props.get(f["general_cost"]),
            props.get(f["plumbing_cost"]),
            props.get(f["electrical_cost"]),
            props.get(f["mechanical_cost"]),
            now,
        )
        if conf is None:
            continue
        permit_num = props.get(f["permit_number"]) or "unknown"
        detail_bits = [
            props.get(f["application_type"]) or "",
            f"issued {issued.isoformat()}" if issued else "",
            props.get(f["address"]) or "",
        ]
        out.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [coords[0], coords[1]]},
                "properties": {
                    "id": f"permit:{permit_num}",
                    "source": "permit",
                    "kind": "porta_potty_likely",
                    "confidence": conf,
                    "name": f"Construction site (permit {permit_num})",
                    "detail": " · ".join(b for b in detail_bits if b),
                    "fetched_at": raw.get("fetched_at"),
                },
            }
        )
    return out
