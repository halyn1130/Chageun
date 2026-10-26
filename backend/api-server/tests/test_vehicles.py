import unittest
from datetime import date
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.routers.vehicles import CATALOG, MaintenanceCreate, router


class VehicleContractTests(unittest.TestCase):
    def test_care_items_and_current_manual_catalog_are_supported(self):
        for item in ('oil_filter', 'cabin_filter', 'brake_fluid'):
            value = MaintenanceCreate(item=item, performed_at='2026-10-23', mileage_km=36200)
            self.assertEqual(value.item, item)
        self.assertIn(dict(manufacturer='기아', model='K5', model_year='2026', powertrain='G2.0'), CATALOG)


class VehicleMileageTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.cursor = self.db.cursor.return_value.__enter__.return_value
        self.vehicle = dict(id=2, nickname='붕붕이', manufacturer='기아', model='K5',
                            model_year='2026', powertrain='G2.0', mileage_km=36200, is_primary=True)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[get_current_user] = lambda: CurrentUser(7, 'test')
        self.client = TestClient(self.app)

    def test_updates_owned_vehicle_and_returns_saved_mileage_without_editing_history(self):
        saved = {**self.vehicle, 'mileage_km': 42000}
        self.cursor.fetchone.side_effect = [self.vehicle, saved]
        response = self.client.patch('/vehicles/2/mileage', json={'mileage_km': 42000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), saved)
        calls = self.cursor.execute.call_args_list
        self.assertEqual(calls[0].args[1], (2, 7))
        self.assertEqual(calls[1].args, (
            'UPDATE vehicles SET mileage_km = %s WHERE id = %s AND user_id = %s', (42000, 2, 7)))
        self.assertFalse(any('maintenance_records' in call.args[0] for call in calls))

    def test_missing_or_other_users_vehicle_is_not_updated(self):
        self.cursor.fetchone.return_value = None
        response = self.client.patch('/vehicles/999/mileage', json={'mileage_km': 42000})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.assertEqual(self.cursor.execute.call_args.args[1], (999, 7))

    def test_requires_login(self):
        del self.app.dependency_overrides[get_current_user]
        response = self.client.patch('/vehicles/2/mileage', json={'mileage_km': 42000})
        self.assertEqual(response.status_code, 401)
        self.db.cursor.assert_not_called()

    def test_invalid_or_missing_readings_never_reach_database(self):
        for value in [-1, 1.5, True, '42', None, 4294967296]:
            with self.subTest(value=value):
                response = self.client.patch('/vehicles/2/mileage', json={'mileage_km': value})
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.patch('/vehicles/2/mileage', json={}).status_code, 422)
        self.db.cursor.assert_not_called()

    def test_zero_reading_is_valid(self):
        self.cursor.fetchone.side_effect = [self.vehicle, {**self.vehicle, 'mileage_km': 0}]
        response = self.client.patch('/vehicles/2/mileage', json={'mileage_km': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mileage_km'], 0)

    def test_exchange_reading_does_not_change_current_vehicle_mileage(self):
        record = dict(id=10, item='engine_oil', performed_at=date(2026, 1, 1), mileage_km=40000, memo=None)
        self.cursor.fetchone.side_effect = [self.vehicle, record]
        response = self.client.post('/vehicles/2/maintenance', json={
            'item': 'engine_oil', 'performed_at': '2026-01-01', 'mileage_km': 40000,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['mileage_km'], 40000)
        calls = self.cursor.execute.call_args_list
        self.assertTrue(any('INSERT INTO maintenance_records' in call.args[0] for call in calls))
        self.assertFalse(any('UPDATE vehicles' in call.args[0] for call in calls))


if __name__ == '__main__':
    unittest.main()
