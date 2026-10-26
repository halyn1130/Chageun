import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException
from pydantic import ValidationError
from app.auth import CurrentUser
from app.routers.settings import PersonalSettings, save_profile

class ProfileTests(unittest.TestCase):
    def test_other_accounts_vehicle_cannot_be_saved(self):
        db = MagicMock()
        cur = db.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [{'id': 1}]
        with self.assertRaises(HTTPException):
            save_profile(PersonalSettings(display_name='테스트', vehicle_id=2), CurrentUser(7,'test'), db)
        self.assertFalse(any(c.args[0].startswith(('INSERT','UPDATE')) for c in cur.execute.call_args_list))

    def test_owned_vehicle_and_preferences_saved_for_verified_user(self):
        db = MagicMock()
        cur = db.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [{'id': 1}]
        result = save_profile(PersonalSettings(display_name='  하린  ', vehicle_id=1), CurrentUser(7,'test'), db)
        self.assertEqual(result['display_name'], '하린')
        writes = [c.args for c in cur.execute.call_args_list if c.args[0].startswith(('INSERT','UPDATE'))]
        self.assertEqual([args for _,args in writes], [(7,'하린'),(1,7),(7,None)])

    def test_blank_name_rejected(self):
        with self.assertRaises(ValidationError): PersonalSettings(display_name='   ')

    def test_no_vehicle_account_can_save_name(self):
        db=MagicMock(); db.cursor.return_value.__enter__.return_value.fetchall.return_value=[]
        self.assertIsNone(save_profile(PersonalSettings(display_name='테스트'),CurrentUser(7,'test'),db)['vehicle_id'])
