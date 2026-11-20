import unittest
from unittest.mock import AsyncMock, MagicMock

import discord
from peewee import SqliteDatabase

from db_utils import db_utils
from discord_utils import now_playing
from models.guild_music_information import Guild
from models.music_information import MusicInformation
from models.queue_object import QueueEntry


class TestProgress(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(now_playing.clock(5), "0:05")
        self.assertEqual(now_playing.clock(213), "3:33")
        self.assertEqual(now_playing.clock(3725), "1:02:05")

    def test_bar_moves_and_never_overflows(self):
        start = now_playing.progress(0, 200)
        middle = now_playing.progress(100, 200)
        end = now_playing.progress(500, 200)

        self.assertTrue(start.startswith("🔘"))
        self.assertIn("1:40 / 3:20", middle)
        self.assertIn("3:20 / 3:20", end)

        for bar in (start, middle, end):
            self.assertEqual(bar.split(" ")[0].count("▬") + 1, now_playing.BAR_CELLS)

    def test_live_has_no_bar(self):
        self.assertIn("LIVE", now_playing.progress(65, None))


class TestControls(unittest.IsolatedAsyncioTestCase):
    async def test_buttons_reflect_state(self):
        view = now_playing.Controls(1)

        view.sync(paused=True, loop_on=True, shuffle_on=False)

        self.assertEqual(str(view.get_item("np:pause").emoji), "▶️")
        self.assertEqual(view.get_item("np:loop").style, discord.ButtonStyle.success)
        self.assertEqual(view.get_item("np:shuffle").style, discord.ButtonStyle.secondary)

    async def test_only_listeners_press_and_not_too_fast(self):
        view = now_playing.Controls(1)
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.guild.voice_client.channel.id = 7
        interaction.user.voice.channel.id = 7

        self.assertTrue(await view.interaction_check(interaction))
        self.assertFalse(await view.interaction_check(interaction))

        view.pressed_at = 0
        interaction.user.voice.channel.id = 8
        self.assertFalse(await view.interaction_check(interaction))


class TestPeek(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SqliteDatabase(':memory:')
        self.binding = self.db.bind_ctx([Guild, QueueEntry])
        self.binding.__enter__()
        self.db.create_tables([Guild, QueueEntry])
        Guild.create(id=1, loop_queue=False, shuffle_queue=False, volume=1.0, bass_boost=1.0)

        for index, force in ((1, False), (2, False), (3, True)):
            QueueEntry.create(guild=1, url=f"u{index}", title=f"t{index}", already_played=False, force_play=force)

    def tearDown(self):
        self.binding.__exit__(None, None, None)

    async def test_peek_matches_what_plays_and_takes_nothing(self):
        peeked = await db_utils.peek_queue_entry(1)

        self.assertEqual(peeked.url, "u3")
        self.assertEqual(await db_utils.count_remaining(1), 3)
        self.assertEqual(await db_utils.get_queue_entry(1), "u3")
        self.assertEqual((await db_utils.peek_queue_entry(1)).url, "u1")
        self.assertEqual(await db_utils.count_remaining(1), 2)

    async def test_render_shows_track_progress_and_state(self):
        Guild.update(loop_queue=True).execute()
        message = MagicMock()
        message.channel.guild.voice_client.is_paused.return_value = False
        source = MagicMock(elapsed=60, volume=0.8)
        track = MusicInformation("s", "Song", "Artist", "https://img", duration=180, webpage_url="https://youtu.be/x")
        panel = now_playing.Panel(message=message, view=now_playing.Controls(1), track=track, source=source)

        embed = await now_playing.render(1, panel)

        self.assertEqual(embed.title, "Song")
        self.assertIn("1:00 / 3:00", embed.description)
        self.assertEqual(embed.fields[0].value, "t3")
        self.assertIn("80%", embed.footer.text)
        self.assertIn("Loop on", embed.footer.text)
        self.assertEqual(panel.view.get_item("np:loop").style, discord.ButtonStyle.success)

    async def test_no_peek_while_shuffling(self):
        Guild.update(shuffle_queue=True).execute()

        self.assertIsNone(await db_utils.peek_queue_entry(1))


if __name__ == '__main__':
    unittest.main()
