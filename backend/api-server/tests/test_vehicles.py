import unittest

from app.routers.vehicles import CATALOG, MaintenanceCreate


class VehicleContractTests(unittest.TestCase):
    def test_care_items_and_current_manual_catalog_are_supported(self):
        for item in ('oil_filter', 'cabin_filter', 'brake_fluid'):
            value = MaintenanceCreate(item=item, performed_at='2026-10-23', mileage_km=36200)
            self.assertEqual(value.item, item)
        self.assertIn(dict(manufacturer='기아', model='K5', model_year='2026', powertrain='G2.0'), CATALOG)


if __name__ == '__main__':
    unittest.main()
