import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from media import argonfetch


class AsyncCM:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *exc_info):
        return False


class FakeResponse:
    def __init__(self, status, payload=None, raises=False):
        self.status = status
        self._payload = payload or {}
        self._raises = raises

    async def json(self):
        if self._raises:
            raise ValueError("not json")
        return self._payload


class TestBaseUrl(unittest.TestCase):
    def test_defaults_to_the_sidecar(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(argonfetch.base_url(), argonfetch.DEFAULT_BASE_URL)

    def test_env_override_loses_its_trailing_slash(self):
        with patch.dict(os.environ, {"ARGONFETCH_URL": "https://app.argonfetch.dev/"}):
            self.assertEqual(argonfetch.base_url(), "https://app.argonfetch.dev")


class TestRaiseForStatus(unittest.IsolatedAsyncioTestCase):
    async def test_404_is_not_found(self):
        with self.assertRaises(argonfetch.NotFound):
            await argonfetch._raise_for_status(FakeResponse(404), "q")

    async def test_415_keeps_the_reason(self):
        response = FakeResponse(415, {"detail": "This media is DRM protected and cannot be downloaded."})

        with self.assertRaises(argonfetch.Unsupported) as caught:
            await argonfetch._raise_for_status(response, "q")

        self.assertIn("DRM", str(caught.exception))

    async def test_415_without_detail_still_explains(self):
        with self.assertRaises(argonfetch.Unsupported) as caught:
            await argonfetch._raise_for_status(FakeResponse(415), "q")

        self.assertTrue(str(caught.exception))

    async def test_502_is_unavailable(self):
        with self.assertRaises(argonfetch.Unavailable):
            await argonfetch._raise_for_status(FakeResponse(502), "q")

    async def test_non_json_body_does_not_mask_the_status(self):
        with self.assertRaises(argonfetch.NotFound):
            await argonfetch._raise_for_status(FakeResponse(404, raises=True), "q")


class TestResolveRetries(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def session_returning(*responses):
        session = MagicMock()
        session.get = MagicMock(side_effect=[AsyncCM(response) for response in responses])
        return MagicMock(return_value=AsyncCM(session)), session

    @patch('media.argonfetch.asyncio.sleep', new_callable=AsyncMock)
    async def test_503_retries_then_gives_up(self, mock_sleep):
        factory, session = self.session_returning(*[FakeResponse(503)] * argonfetch.MAINTENANCE_RETRIES)

        with patch('media.argonfetch.aiohttp.ClientSession', factory):
            with self.assertRaises(argonfetch.Unavailable):
                await argonfetch.resolve("q")

        self.assertEqual(session.get.call_count, argonfetch.MAINTENANCE_RETRIES)
        self.assertEqual(mock_sleep.await_count, argonfetch.MAINTENANCE_RETRIES - 1)

    @patch('media.argonfetch.asyncio.sleep', new_callable=AsyncMock)
    async def test_503_then_success_returns_the_payload(self, mock_sleep):
        factory, session = self.session_returning(
            FakeResponse(503),
            FakeResponse(200, {"type": "Media", "mediaItems": []}),
        )

        with patch('media.argonfetch.aiohttp.ClientSession', factory):
            result = await argonfetch.resolve("q")

        self.assertEqual(result["type"], "Media")
        self.assertEqual(session.get.call_count, 2)

    async def test_connection_error_is_unavailable(self):
        session = MagicMock()
        session.get = MagicMock(side_effect=argonfetch.aiohttp.ClientError("boom"))
        factory = MagicMock(return_value=AsyncCM(session))

        with patch('media.argonfetch.aiohttp.ClientSession', factory):
            with self.assertRaises(argonfetch.Unavailable):
                await argonfetch.resolve("q")


class TestTrackFrom(unittest.TestCase):
    def test_blank_cover_becomes_none(self):
        track = argonfetch.track_from({"title": "T", "author": "A", "coverUrl": ""}, "fallback")

        self.assertIsNone(track.image_url)

    def test_missing_url_falls_back(self):
        track = argonfetch.track_from({"title": "T"}, "https://example.com/song")

        self.assertEqual(track.url, "https://example.com/song")
        self.assertEqual(track.author, "")

    def test_missing_title_is_unknown(self):
        self.assertEqual(argonfetch.track_from({}, "u").title, "Unknown")


class TestBestAudioUrl(unittest.TestCase):
    def test_ignores_renditions_without_a_key(self):
        item = {"audio": {"renditions": [{"bitrate": 999, "convertTo": None}]}}

        self.assertIsNone(argonfetch.best_audio_url(item))

    def test_falls_back_when_only_transcodes_exist(self):
        item = {"audio": {"renditions": [{"key": "k", "bitrate": 192, "convertTo": "mp3"}]}}

        self.assertIsNone(argonfetch.best_audio_url(item))

    def test_builds_the_media_stream_path(self):
        item = {"audio": {"renditions": [{"key": "abc", "bitrate": 128, "convertTo": None}]}}

        with patch.dict(os.environ, {"ARGONFETCH_URL": "http://af:8080"}):
            self.assertEqual(argonfetch.best_audio_url(item), "http://af:8080/api/Stream/Media/abc")


if __name__ == '__main__':
    unittest.main()
