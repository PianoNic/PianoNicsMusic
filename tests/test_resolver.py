import unittest
from unittest.mock import AsyncMock, patch

from media import argonfetch, resolver


class TestNormalizeQuery(unittest.TestCase):
    def test_watch_with_playlist_becomes_playlist(self):
        result = resolver.normalize_query("https://www.youtube.com/watch?v=abc&list=PL123")
        self.assertIn("/playlist", result)
        self.assertIn("list=PL123", result)

    def test_radio_mix_is_left_alone(self):
        query = "https://www.youtube.com/watch?v=abc&list=RD123"
        self.assertEqual(resolver.normalize_query(query), query)

    def test_plain_watch_is_left_alone(self):
        query = "https://www.youtube.com/watch?v=abc"
        self.assertEqual(resolver.normalize_query(query), query)

    def test_search_term_is_left_alone(self):
        self.assertEqual(resolver.normalize_query("never gonna give you up"), "never gonna give you up")

    def test_other_hosts_are_left_alone(self):
        query = "https://soundcloud.com/artist/track?list=PL123&v=abc"
        self.assertEqual(resolver.normalize_query(query), query)


class TestBestAudioUrl(unittest.TestCase):
    def test_prefers_source_over_transcode(self):
        item = {
            "audio": {
                "renditions": [
                    {"key": "source", "bitrate": 128.93, "convertTo": None},
                    {"key": "source", "bitrate": 192, "convertTo": "mp3"},
                ]
            }
        }
        self.assertTrue(argonfetch.best_audio_url(item).endswith("/api/Stream/Media/source"))

    def test_picks_highest_source_bitrate(self):
        item = {
            "audio": {
                "renditions": [
                    {"key": "low", "bitrate": 46.2, "convertTo": None},
                    {"key": "high", "bitrate": 129.5, "convertTo": None},
                ]
            }
        }
        self.assertTrue(argonfetch.best_audio_url(item).endswith("/api/Stream/Media/high"))

    def test_no_renditions_returns_none(self):
        self.assertIsNone(argonfetch.best_audio_url({"audio": None}))


class TestGetPlayable(unittest.IsolatedAsyncioTestCase):
    @patch('media.argonfetch.resolve', new_callable=AsyncMock)
    async def test_direct_file_falls_back_to_source_url(self, mock_resolve):
        mock_resolve.return_value = {
            "mediaItems": [
                {"requestedUrl": "https://example.com/song.mp3", "title": "Song", "author": "", "audio": None}
            ]
        }
        result = await resolver.get_playable("https://example.com/song.mp3")
        self.assertEqual(result.streaming_url, "https://example.com/song.mp3")
        self.assertEqual(result.author, "Unknown")

    @patch('media.argonfetch.resolve', new_callable=AsyncMock)
    async def test_missing_item_raises_not_found(self, mock_resolve):
        mock_resolve.return_value = {"mediaItems": []}
        with self.assertRaises(argonfetch.NotFound):
            await resolver.get_playable("https://example.com/gone")


class TestGetTracks(unittest.IsolatedAsyncioTestCase):
    @patch('media.resolver.max_tracks', return_value=2)
    @patch('media.argonfetch.resolve', new_callable=AsyncMock)
    async def test_caps_long_playlists(self, mock_resolve, _):
        mock_resolve.return_value = {
            "mediaItems": [
                {"requestedUrl": f"u{i}", "title": f"t{i}", "author": "a"} for i in range(5)
            ]
        }
        tracks, dropped = await resolver.get_tracks("https://example.com/list")
        self.assertEqual(len(tracks), 2)
        self.assertEqual(dropped, 3)


if __name__ == '__main__':
    unittest.main()
