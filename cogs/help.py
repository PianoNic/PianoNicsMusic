import discord
from discord.ext import commands

from discord_utils import responses
from utils import get_full_version_info

COMMANDS = [
    ("play", "Plays the provided audio"),
    ("force_play", "Force plays the provided audio"),
    ("pause", "Pauses the currently playing audio"),
    ("resume", "Resumes the currently paused audio"),
    ("skip", "Skips the currently playing audio"),
    ("stop", "Stops the currently playing audio"),
    ("leave", "Leaves the voice channel and stops playing audio"),
    ("loop", "Toggles looping of the queue"),
    ("shuffle", "Shuffles the current music queue"),
    ("queue", "Shows the current music queue"),
    ("bot_status", "Shows current bot and queue status"),
    ("volume", "Sets or shows the current volume (0-100)"),
    ("volume_up", "Increases volume by 10%"),
    ("volume_down", "Decreases volume by 10%"),
    ("bass_boost", "Sets or shows the bass boost (0-200)"),
    ("earrape", "Toggles the earrape filter"),
    ("ping", "Checks the bot's latency"),
    ("information", "Shows bot information and version"),
]


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are all the available commands:",
            color=0x282841,
        )

        for name, description in COMMANDS:
            embed.add_field(name=f"/{name}", value=description, inline=False)

        embed.set_footer(text=get_full_version_info())
        await responses.reply(ctx, embed)

    @commands.command(aliases=['h', 'commands', 'command', 'cmds', 'cmd', 'info', 'assist', 'assistme', 'helpme', 'helppls', 'helpmepls', 'helpmeplease', 'helpmeout', 'helpmeoutpls', 'helpmeoutplease'])
    async def help(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="help", description="Shows all available commands")
    async def help_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Help(bot))
