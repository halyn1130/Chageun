import os
import unittest
from unittest.mock import patch
import httpx
from app import tts

class TtsTests(unittest.TestCase):
    def response(self, content=b'RIFF-wave', mime='audio/wav', status=200):
        return httpx.Response(status, content=content, headers={'Content-Type': mime}, request=httpx.Request('POST', 'https://test.invalid'))

    @patch.dict(os.environ, {'TTS_PROVIDER': 'typecast', 'TYPECAST_API_KEY': 'test-key', 'TYPECAST_VOICE_ID': 'tc_test'}, clear=True)
    def test_typecast_smart_korean_wav(self):
        with patch.object(tts.httpx, 'post', return_value=self.response()) as post:
            audio = tts.synthesize('안녕하세요')
        self.assertEqual(audio.media_type, 'audio/wav')
        self.assertEqual(audio.data, b'RIFF-wave')
        args = post.call_args.kwargs
        self.assertEqual(args['headers'], {'X-API-KEY': 'test-key'})
        self.assertEqual(args['json'], {'text': '안녕하세요', 'model': 'ssfm-v30', 'voice_id': 'tc_test', 'language': 'kor', 'prompt': {'emotion_type': 'smart'}, 'output': {'audio_format': 'wav'}})

    @patch.dict(os.environ, {'TTS_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}, clear=True)
    def test_legacy_openai_mp3(self):
        with patch.object(tts.httpx, 'post', return_value=self.response(mime='audio/mpeg')) as post:
            self.assertEqual(tts.synthesize('문장').media_type, 'audio/mpeg')
        self.assertEqual(post.call_args.kwargs['json']['voice'], 'nova')

    @patch.dict(os.environ, {'TTS_PROVIDER': 'typecast'}, clear=True)
    def test_missing_key_never_calls_provider(self):
        with patch.object(tts.httpx, 'post') as post, self.assertRaises(tts.TtsError):
            tts.synthesize('문장')
        post.assert_not_called()

    @patch.dict(os.environ, {'TTS_PROVIDER': 'typecast', 'TYPECAST_API_KEY': 'test-key'}, clear=True)
    def test_provider_error_does_not_expose_body(self):
        with patch.object(tts.httpx, 'post', return_value=self.response(b'secret text', status=402)):
            with self.assertRaises(tts.TtsError) as ctx: tts.synthesize('문장')
        self.assertIn('402', str(ctx.exception))
        self.assertNotIn('secret', str(ctx.exception))

    @patch.dict(os.environ, {'TTS_PROVIDER': 'typecast', 'TYPECAST_API_KEY': 'test-key'}, clear=True)
    def test_invalid_audio_is_rejected(self):
        for res in [self.response(b''), self.response(b'{}', mime='application/json')]:
            with patch.object(tts.httpx, 'post', return_value=res), self.assertRaises(tts.TtsError):
                tts.synthesize('문장')

    @patch.dict(os.environ, {'TTS_PROVIDER':'typecast','TYPECAST_API_KEY':'test-key'}, clear=True)
    def test_selected_voice_overrides_default(self):
        voice='tc_658d1bc867f8ac8fa3cbbeec'
        with patch.object(tts.httpx,'post',return_value=self.response()) as post:
            tts.synthesize('안내',voice_id=voice)
        self.assertEqual(post.call_args.kwargs['json']['voice_id'],voice)
        with patch.object(tts.httpx,'post') as post, self.assertRaises(tts.TtsError):
            tts.synthesize('안내',voice_id='unlisted')
        post.assert_not_called()

if __name__ == '__main__': unittest.main()
