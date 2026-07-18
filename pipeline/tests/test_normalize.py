import unittest

from pipeline.normalize import build_collection, dedupe, haversine_m


def feature(fid, lon, lat, kind="restroom", confidence=0.5):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "id": fid,
            "source": "osm",
            "kind": kind,
            "confidence": confidence,
            "name": fid,
            "detail": "",
            "fetched_at": "2026-07-18T00:00:00+00:00",
        },
    }


class DedupeTest(unittest.TestCase):
    def test_same_kind_nearby_keeps_higher_confidence(self):
        a = feature("a", -79.7883, 36.0740, confidence=0.9)
        b = feature("b", -79.78832, 36.07405, confidence=0.7)  # ~7m away
        kept = dedupe([b, a])
        self.assertEqual([f["properties"]["id"] for f in kept], ["a"])

    def test_different_kind_nearby_both_kept(self):
        a = feature("a", -79.7883, 36.0740, kind="restroom")
        b = feature("b", -79.78832, 36.07405, kind="porta_potty_likely")
        self.assertEqual(len(dedupe([a, b])), 2)

    def test_far_apart_both_kept(self):
        a = feature("a", -79.7883, 36.0740)
        b = feature("b", -79.8083, 36.0885)  # ~2.4 km
        self.assertEqual(len(dedupe([a, b])), 2)

    def test_haversine_sanity(self):
        # ~111 km per degree of latitude
        d = haversine_m(-79.79, 36.0, -79.79, 37.0)
        self.assertAlmostEqual(d, 111_000, delta=1000)


class BuildCollectionTest(unittest.TestCase):
    def test_valid_geojson_with_metadata_and_stable_order(self):
        coll = build_collection(
            {"osm_toilets": [feature("b", -79.8, 36.1), feature("a", -79.7, 36.0)]},
            generated_at="2026-07-18T00:00:00+00:00",
        )
        self.assertEqual(coll["type"], "FeatureCollection")
        self.assertEqual(coll["metadata"]["counts"], {"osm_toilets": 2})
        self.assertEqual(coll["metadata"]["total_after_dedupe"], 2)
        self.assertEqual(
            [f["properties"]["id"] for f in coll["features"]], ["a", "b"]
        )


if __name__ == "__main__":
    unittest.main()
