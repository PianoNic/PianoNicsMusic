import logging

import discord
from discord.ext import commands

from discord_utils import responses

logger = logging.getLogger('PianoNicsMusic')


class Skip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if not voice_client:
            await responses.not_connected(ctx)
            return

        voice_client.stop()
        await responses.confirm(ctx, "⏭️", "Skipped", "Skipped Song")

    @commands.command(aliases=['next', 'advance', 'skip_song', 'move_on', 'play_next'])
    async def skip(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="skip", description="Skips the currently playing audio")
    async def skip_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Skip(bot))
