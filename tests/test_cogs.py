import asyncio
import unittest

import discord
from discord.ext import commands

from cogs import COGS


def build_bot():
    # Bot() reaches for the running loop, and an IsolatedAsyncioTestCase elsewhere
    # in the suite will have closed it.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    bot = commands.Bot(command_prefix='.', intents=discord.Intents.none(), help_command=None)

    for cog in COGS:
        bot.load_extension(cog)

    return bot


class TestCogRegistry(unittest.TestCase):
    def test_every_cog_file_is_registered(self):
        from pathlib import Path

        on_disk = {
            f"cogs.{path.stem}"
            for path in Path('cogs').glob('*.py')
            if path.stem != '__init__'
        }

        self.assertEqual(on_disk, set(COGS))


class TestCogsLoad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = build_bot()

    def test_every_cog_loads(self):
        self.assertEqual(len(self.bot.extensions), len(COGS))

    def test_every_command_has_a_slash_twin(self):
        prefix_names = {command.name for command in self.bot.commands}
        slash_names = {command.name for command in self.bot.pending_application_commands}

        self.assertEqual(prefix_names, slash_names)

    def test_expected_commands_are_registered(self):
        expected = {
            'play', 'force_play', 'pause', 'resume', 'skip', 'stop', 'leave',
            'loop', 'shuffle', 'queue', 'bot_status', 'volume', 'volume_up',
            'volume_down', 'bass_boost', 'bass_boost_up', 'bass_boost_down',
            'earrape', 'help', 'ping', 'information',
        }

        self.assertEqual({command.name for command in self.bot.commands}, expected)

    def test_no_duplicate_aliases(self):
        seen = {}

        for command in self.bot.commands:
            for name in [command.name, *command.aliases]:
                self.assertNotIn(name, seen, f"{name} is claimed by both {seen.get(name)} and {command.name}")
                seen[name] = command.name

    def test_help_lists_only_real_commands(self):
        from cogs.help import COMMANDS

        registered = {command.name for command in self.bot.commands}

        for name, _ in COMMANDS:
            self.assertIn(name, registered, f"help advertises {name}, which is not registered")

    def test_events_cog_registers_listeners(self):
        listeners = {name for name, _ in self.bot.get_cog('Events').get_listeners()}

        self.assertIn('on_ready', listeners)
        self.assertIn('on_error', listeners)
        self.assertIn('on_command_error', listeners)


if __name__ == '__main__':
    unittest.main()
