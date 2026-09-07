import logging

import discord
from discord.ext import commands

from discord_utils import responses

logger = logging.getLogger('PianoNicsMusic')


class Resume(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if not voice_client:
            await responses.not_connected(ctx)
            return

        voice_client.resume()
        await responses.confirm(ctx, "▶️", "Resumed", "Resumed the music")

    @commands.command(aliases=['continue', 'unpause', 'proceed', 'restart', 'go', 'resume_playback'])
    async def resume(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="resume", description="Resumes the currently paused audio")
    async def resume_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Resume(bot))
