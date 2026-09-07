import logging

import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from cogs.play import resolve_tracks
from discord_utils import responses

logger = logging.getLogger('PianoNicsMusic')


class ForcePlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx, query, insta_skip):
        guild = await db_utils.get_guild(ctx.guild.id)
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if not guild or not voice_client:
            await responses.not_connected(ctx)
            return

        if not query:
            await responses.fail(ctx, "Missing Input", "Please provide a query.")
            return

        tracks, _ = await resolve_tracks(ctx, query)

        if not tracks:
            return

        await db_utils.add_force_next_play_to_queue(ctx.guild.id, tracks[0])

        if insta_skip:
            await responses.confirm(ctx, "⏭️", "Force Playing", "Force playing Song")
            voice_client.stop()
        else:
            await responses.confirm(ctx, "📥", "Queued", "Playing next up")

    @commands.command(aliases=['fp', 'forceplay', 'playforce'])
    async def force_play(self, ctx, *, query=None):
        await self.run(ctx, query, False)

    @discord.slash_command(name="force_play", description="Plays a song right after the current one finishes")
    async def force_play_slash(self, ctx, query: str, insta_skip: bool = False):
        await ctx.defer()
        await self.run(ctx, query, insta_skip)


def setup(bot):
    bot.add_cog(ForcePlay(bot))
