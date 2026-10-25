import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.auth import CurrentUser
from app.routers.settings import get_voice, save_voice, VoicePreference, VOICES
class SettingsTests(unittest.TestCase):
    def test_account_is_taken_from_verified_user(self):
        db=MagicMock();cur=db.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value={'voice_id':VOICES[0]['voice_id']}
        self.assertEqual(get_voice(CurrentUser(7,'test'),db)['voice_id'],VOICES[0]['voice_id'])
        self.assertEqual(cur.execute.call_args.args[1],(7,))
        save_voice(VoicePreference(voice_id=VOICES[1]['voice_id']),CurrentUser(8,'other'),db)
        self.assertEqual(cur.execute.call_args.args[1],(8,VOICES[1]['voice_id']))
    def test_invalid_voice_does_not_write(self):
        db=MagicMock()
        with self.assertRaises(HTTPException) as e: save_voice(VoicePreference(voice_id='wrong'),CurrentUser(7,'test'),db)
        self.assertEqual(e.exception.status_code,422);db.cursor.assert_not_called()
    def test_default_is_nullable(self):
        db=MagicMock();db.cursor.return_value.__enter__.return_value.fetchone.return_value=None
        self.assertEqual(get_voice(CurrentUser(7,'test'),db),{'voice_id':None})
if __name__=='__main__':unittest.main()
