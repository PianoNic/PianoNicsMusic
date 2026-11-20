import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from media import resolver


class AsyncCM:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *exc_info):
        return False


class TestNormalizeQuery(unittest.TestCase):
    def test_watch_with_playlist_becomes_playlist(self):
        result = resolver.normalize_query("https://www.youtube.com/watch?v=abc&list=PL123")
        self.assertIn("/playlist", result)
        self.assertIn("list=PL123", result)

    def test_radio_mix_keeps_its_watch_link(self):
        query = "https://www.youtube.com/watch?v=abc&list=RD123"
        self.assertEqual(resolver.normalize_query(query), query)

    def test_plain_watch_is_left_alone(self):
        query = "https://www.youtube.com/watch?v=abc"
        self.assertEqual(resolver.normalize_query(query), query)

    def test_other_hosts_are_left_alone(self):
        query = "https://soundcloud.com/artist/track?list=PL123&v=abc"
        self.assertEqual(resolver.normalize_query(query), query)


class TestErrorFrom(unittest.TestCase):
    def test_maps_known_failures(self):
        self.assertIsInstance(resolver.error_from("ERROR: This video is DRM protected"), resolver.Unsupported)
        self.assertIsInstance(resolver.error_from("ERROR: [generic] Unsupported URL: x"), resolver.Unsupported)
        self.assertIsInstance(resolver.error_from("ERROR: [youtube] abc: Video unavailable"), resolver.NotFound)
        self.assertIsInstance(resolver.error_from("ERROR: something new"), resolver.Unavailable)


class TestEnsurePublic(unittest.IsolatedAsyncioTestCase):
    async def test_refuses_private_networks(self):
        for url in ("http://127.0.0.1/x", "http://localhost:8080/", "http://192.168.1.1/a.mp3"):
            with self.subTest(url=url), self.assertRaises(resolver.Unsupported):
                await resolver.ensure_public(url)

    async def test_allows_public_addresses(self):
        await resolver.ensure_public("http://1.1.1.1/a.mp3")


class TestGetTracks(unittest.IsolatedAsyncioTestCase):
    @patch('media.resolver.ytdlp', new_callable=AsyncMock)
    async def test_search_text_is_a_youtube_search_after_double_dash(self, mock_ytdlp):
        mock_ytdlp.return_value = {"entries": [{"url": "https://youtu.be/x", "title": "T", "uploader": "A"}]}

        tracks, dropped = await resolver.get_tracks("--exec rm never gonna")

        args = mock_ytdlp.await_args.args
        self.assertEqual(args[-2:], ("--", "ytsearch1:--exec rm never gonna"))
        self.assertEqual(tracks[0].url, "https://youtu.be/x")
        self.assertEqual(dropped, 0)

    @patch('media.resolver.max_tracks', return_value=2)
    @patch('media.resolver.ensure_public', new_callable=AsyncMock)
    @patch('media.resolver.ytdlp', new_callable=AsyncMock)
    async def test_caps_long_playlists(self, mock_ytdlp, _, __):
        mock_ytdlp.return_value = {
            "playlist_count": 5,
            "entries": [{"url": f"u{i}", "title": f"t{i}"} for i in range(2)],
        }

        tracks, dropped = await resolver.get_tracks("https://example.com/list")

        self.assertEqual(len(tracks), 2)
        self.assertEqual(dropped, 3)

    @patch('media.resolver.spotify_tracks', new_callable=AsyncMock)
    async def test_spotify_links_go_to_spotify(self, mock_spotify):
        mock_spotify.return_value = ([resolver.Track("https://music.youtube.com/search?q=A%20T#songs", "T", "A", None)], 1)

        await resolver.get_tracks("https://open.spotify.com/intl-de/track/3h5T5JypYU7huFiVYhv1dr?si=x")

        mock_spotify.assert_awaited_with("track", "3h5T5JypYU7huFiVYhv1dr")

    @patch('media.resolver.spotify_tracks', new_callable=AsyncMock)
    async def test_capped_spotify_playlist_reports_dropped(self, mock_spotify):
        track = resolver.Track("u", "T", "A", None)
        mock_spotify.return_value = ([track] * 500, 1223)

        tracks, dropped = await resolver.get_tracks("https://open.spotify.com/playlist/abc")

        self.assertEqual((len(tracks), dropped), (500, 723))


class TestSpotifyTracks(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def embed_page(count):
        entity = {"type": "playlist", "trackList": [{"title": f"t{i}", "subtitle": "A, B"} for i in range(count)]}
        data = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
        return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'

    async def run_with(self, count, web):
        response = MagicMock()
        response.text = AsyncMock(return_value=self.embed_page(count))
        session = MagicMock()
        session.get = MagicMock(return_value=AsyncCM(response))

        with patch('media.resolver.aiohttp.ClientSession', MagicMock(return_value=AsyncCM(session))),                 patch('media.resolver.spotify_web.playlist_tracks', web):
            return await resolver.spotify_tracks("playlist", "id")

    async def test_short_playlist_skips_the_web_player(self):
        web = AsyncMock()
        tracks, total = await self.run_with(3, web)

        web.assert_not_awaited()
        self.assertEqual(tracks[0].author, "A, B")
        self.assertIn("music.youtube.com/search", tracks[0].url)
        self.assertEqual(total, 3)

    async def test_full_page_asks_the_web_player(self):
        tracks, total = await self.run_with(100, AsyncMock(return_value=([("x", "y")] * 250, 1223)))

        self.assertEqual(len(tracks), 250)
        self.assertEqual(total, 1223)

    async def test_web_player_failure_keeps_the_embed_list(self):
        tracks, total = await self.run_with(100, AsyncMock(side_effect=RuntimeError("secret moved")))

        self.assertEqual((len(tracks), total), (100, 100))


class TestGetPlayable(unittest.IsolatedAsyncioTestCase):
    @patch('media.resolver.ytdlp', new_callable=AsyncMock)
    async def test_search_takes_first_entry_and_keeps_headers(self, mock_ytdlp):
        mock_ytdlp.return_value = {"entries": [{"url": "https://cdn/x", "title": "T", "http_headers": {"User-Agent": "u"}}]}

        result = await resolver.get_playable("ytsearch1:A - T")

        self.assertEqual(result.streaming_url, "https://cdn/x")
        self.assertEqual(result.author, "Unknown")
        self.assertEqual(result.http_headers, {"User-Agent": "u"})

    @patch('media.resolver.ytdlp', new_callable=AsyncMock)
    async def test_missing_item_raises_not_found(self, mock_ytdlp):
        mock_ytdlp.return_value = {"entries": []}

        with self.assertRaises(resolver.NotFound):
            await resolver.get_playable("ytsearch1:nothing")


class TestPrefetch(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        resolver._prefetched.clear()

    @patch('media.resolver.resolve_playable', new_callable=AsyncMock)
    async def test_play_reuses_the_prefetch(self, mock_resolve):
        mock_resolve.return_value = "info"

        resolver.prefetch("https://youtu.be/x")
        resolver.prefetch("https://youtu.be/x")

        self.assertEqual(await resolver.get_playable("https://youtu.be/x"), "info")
        self.assertEqual(mock_resolve.await_count, 1)

    @patch('media.resolver.resolve_playable', new_callable=AsyncMock)
    async def test_failed_prefetch_resolves_again(self, mock_resolve):
        mock_resolve.side_effect = [resolver.Unavailable("flaky"), "info"]

        resolver.prefetch("u")

        self.assertEqual(await resolver.get_playable("u"), "info")

    @patch('media.resolver.time.monotonic')
    @patch('media.resolver.resolve_playable', new_callable=AsyncMock)
    async def test_stale_prefetch_is_not_used(self, mock_resolve, mock_clock):
        mock_resolve.return_value = "fresh"
        mock_clock.return_value = 0
        resolver.prefetch("u")
        stale_task = resolver._prefetched["u"][1]
        mock_clock.return_value = resolver.PREFETCH_MAX_AGE_SECONDS + 1

        self.assertEqual(await resolver.get_playable("u"), "fresh")
        await asyncio.sleep(0)
        self.assertTrue(stale_task.cancelled())


if __name__ == '__main__':
    unittest.main()
