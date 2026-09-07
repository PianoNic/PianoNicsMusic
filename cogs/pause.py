import logging

import discord
from discord.ext import commands

from discord_utils import responses

logger = logging.getLogger('PianoNicsMusic')


class Pause(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if not voice_client:
            await responses.not_connected(ctx)
            return

        voice_client.pause()
        await responses.confirm(ctx, "⏸️", "Paused", "Paused the music")

    @commands.command(aliases=['hold', 'freeze', 'break', 'wait', 'intermission'])
    async def pause(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="pause", description="Pauses the currently playing audio")
    async def pause_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Pause(bot))
