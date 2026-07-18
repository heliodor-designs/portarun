import datetime
import json
import pathlib
import unittest

from pipeline.sources import arcgis, greensboro_parks, greensboro_permits, osm_toilets

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
# Fixtures were authored relative to this date; pin it so tests don't age out.
NOW = datetime.date(2026, 7, 18)


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


class PermitsTest(unittest.TestCase):
    def setUp(self):
        self.features = greensboro_permits.parse(load("greensboro_permits"), now=NOW)
        self.by_id = {f["properties"]["id"]: f for f in self.features}

    def test_excludes_finaled_old_and_geometryless(self):
        self.assertNotIn("permit:202523237", self.by_id)  # final inspection made
        self.assertNotIn("permit:202403998", self.by_id)  # issued outside the window
        self.assertNotIn("permit:202609999", self.by_id)  # no geometry
        self.assertEqual(len(self.features), 4)

    def test_new_commercial_scores_higher_than_trade_work(self):
        big = self.by_id["permit:202607903"]["properties"]["confidence"]
        reno = self.by_id["permit:202611026"]["properties"]["confidence"]
        self.assertGreater(big, reno)
        self.assertEqual(big, 0.8)
        self.assertEqual(reno, 0.35)

    def test_plumbing_renovation_scores_higher_than_other_trades(self):
        issued = datetime.date(2026, 7, 1)  # within MAX_AGE_DAYS of NOW
        # An alteration whose only trade cost is plumbing: the building's own
        # toilets are out of service, so the odds of a site toilet rise.
        plumbing = greensboro_permits.confidence(
            "Issued", "Int/Ext Alterations", "R", "N", issued, 12000,
            0, 6000, 0, 0, NOW,
        )
        # The same alteration but electrical-only: no general work, no plumbing.
        electrical = greensboro_permits.confidence(
            "Issued", "Int/Ext Alterations", "R", "N", issued, 12000,
            0, 0, 6000, 0, NOW,
        )
        self.assertEqual(plumbing, 0.35)  # base 0.3 + plumbing 0.05
        self.assertEqual(electrical, 0.15)  # base 0.3 - trade-only 0.15

    def test_schema(self):
        for f in self.features:
            props = f["properties"]
            self.assertEqual(props["source"], "permit")
            self.assertEqual(props["kind"], "porta_potty_likely")
            self.assertLessEqual(props["confidence"], 0.9)
            self.assertEqual(len(f["geometry"]["coordinates"]), 2)

    def test_confidence_none_for_unissued(self):
        self.assertIsNone(
            greensboro_permits.confidence(
                "Applied", "New Construction", "C", "N",
                datetime.date(2026, 6, 1), 1_000_000, 500_000, 0, 0, 0, NOW,
            )
        )


class ParksTest(unittest.TestCase):
    def test_only_parks_with_restrooms(self):
        features = greensboro_parks.parse(load("greensboro_parks"))
        names = {f["properties"]["name"] for f in features}
        self.assertEqual(len(features), 4)
        self.assertIn("Lake Daniel Park restroom", names)
        self.assertNotIn("Sternberger Park restroom", names)
        for f in features:
            self.assertEqual(f["properties"]["kind"], "restroom")
            self.assertEqual(f["properties"]["confidence"], 0.9)


class OsmTest(unittest.TestCase):
    def setUp(self):
        self.features = osm_toilets.parse(load("osm_toilets"))
        self.by_id = {f["properties"]["id"]: f for f in self.features}

    def test_excludes_private(self):
        self.assertNotIn("osm:node/9876543212", self.by_id)
        self.assertEqual(len(self.features), 3)

    def test_way_uses_center(self):
        way = self.by_id["osm:way/123456789"]
        self.assertEqual(way["geometry"]["coordinates"], [-79.8433, 36.1461])

    def test_access_yes_scores_higher(self):
        lebauer = self.by_id["osm:node/9876543210"]["properties"]["confidence"]
        untagged = self.by_id["osm:node/9876543211"]["properties"]["confidence"]
        self.assertGreater(lebauer, untagged)


class ArcgisHelpersTest(unittest.TestCase):
    def test_check_fields_reports_missing_and_actual(self):
        meta = {"fields": [{"name": "OBJECTID"}, {"name": "PermitNbr"}]}
        with self.assertRaises(arcgis.FieldMapError) as ctx:
            arcgis.check_fields(meta, {"permit_number": "PermitNum"}, "test-layer")
        self.assertIn("PermitNum", str(ctx.exception))
        self.assertIn("PermitNbr", str(ctx.exception))

    def test_epoch_ms_and_iso_dates(self):
        self.assertEqual(
            arcgis.epoch_ms_to_date(1770724800000), datetime.date(2026, 2, 10)
        )
        self.assertEqual(
            arcgis.epoch_ms_to_date("2026-02-10"), datetime.date(2026, 2, 10)
        )
        self.assertIsNone(arcgis.epoch_ms_to_date(None))


if __name__ == "__main__":
    unittest.main()
