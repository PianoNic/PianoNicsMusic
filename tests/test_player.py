import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from discord_utils import player


class TestBuildFilter(unittest.IsolatedAsyncioTestCase):
    @patch('discord_utils.player.db_utils.get_earrape', new_callable=AsyncMock)
    @patch('discord_utils.player.db_utils.get_bass_boost', new_callable=AsyncMock)
    async def test_neutral_bass_is_no_gain(self, mock_bass, mock_earrape):
        mock_bass.return_value = 1.0
        mock_earrape.return_value = False

        self.assertIn("g=0.0", await player.build_filter(1))

    @patch('discord_utils.player.db_utils.get_earrape', new_callable=AsyncMock)
    @patch('discord_utils.player.db_utils.get_bass_boost', new_callable=AsyncMock)
    async def test_maximum_bass_boosts(self, mock_bass, mock_earrape):
        mock_bass.return_value = 2.0
        mock_earrape.return_value = False

        self.assertIn("g=12.0", await player.build_filter(1))

    @patch('discord_utils.player.db_utils.get_earrape', new_callable=AsyncMock)
    @patch('discord_utils.player.db_utils.get_bass_boost', new_callable=AsyncMock)
    async def test_zero_bass_cuts(self, mock_bass, mock_earrape):
        mock_bass.return_value = 0.0
        mock_earrape.return_value = False

        self.assertIn("g=-12.0", await player.build_filter(1))

    @patch('discord_utils.player.db_utils.get_earrape', new_callable=AsyncMock)
    @patch('discord_utils.player.db_utils.get_bass_boost', new_callable=AsyncMock)
    async def test_earrape_appends_the_crusher(self, mock_bass, mock_earrape):
        mock_bass.return_value = 1.0
        mock_earrape.return_value = True

        audio_filter = await player.build_filter(1)

        self.assertIn("acrusher", audio_filter)
        self.assertIn("loudnorm", audio_filter)

    @patch('discord_utils.player.db_utils.get_earrape', new_callable=AsyncMock)
    @patch('discord_utils.player.db_utils.get_bass_boost', new_callable=AsyncMock)
    async def test_filter_is_free_of_quotes(self, mock_bass, mock_earrape):
        mock_bass.return_value = 1.5
        mock_earrape.return_value = True

        self.assertNotIn('"', await player.build_filter(1))


class TestWaitUntilFinished(unittest.IsolatedAsyncioTestCase):
    async def test_returns_when_the_track_finishes(self):
        voice_client = MagicMock()
        voice_client.is_connected.return_value = True

        finished = asyncio.Event()
        waiter = asyncio.create_task(player.wait_until_finished(voice_client, finished))

        await asyncio.sleep(0)
        finished.set()

        await asyncio.wait_for(waiter, timeout=1)

    async def test_returns_when_the_client_disconnects(self):
        voice_client = MagicMock()
        voice_client.is_connected.return_value = False

        await asyncio.wait_for(
            player.wait_until_finished(voice_client, asyncio.Event()), timeout=1
        )

    async def test_does_not_return_while_still_playing(self):
        voice_client = MagicMock()
        voice_client.is_connected.return_value = True

        waiter = asyncio.create_task(player.wait_until_finished(voice_client, asyncio.Event()))
        await asyncio.sleep(0.05)

        self.assertFalse(waiter.done())

        waiter.cancel()


if __name__ == '__main__':
    unittest.main()
