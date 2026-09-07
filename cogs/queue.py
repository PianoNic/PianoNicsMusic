import logging

import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import responses
from utils import get_full_version_info

logger = logging.getLogger('PianoNicsMusic')

SHOWN = 10


class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        entries = await db_utils.get_queue(ctx.guild.id)

        if not entries:
            await responses.reply(
                ctx,
                discord.Embed(title="🎶 Queue", description="The queue is currently empty.", color=0x282841),
            )
            return

        embed = discord.Embed(title="🎶 Current Queue", color=0x282841)

        upcoming = [entry for entry in entries if not entry.already_played]
        played = [entry for entry in entries if entry.already_played]

        if played:
            now = played[-1]
            embed.add_field(name="Now Playing", value=f"[{now.title or 'Unknown'}]({now.url})", inline=False)

        if upcoming:
            for index, entry in enumerate(upcoming[:SHOWN], start=1):
                embed.add_field(name=f"#{index}", value=f"[{entry.title or 'Unknown'}]({entry.url})", inline=False)

            if len(upcoming) > SHOWN:
                embed.add_field(name="...", value=f"And {len(upcoming) - SHOWN} more...", inline=False)
        else:
            embed.add_field(name="Up Next", value="No more songs in the queue.", inline=False)

        embed.set_footer(text=get_full_version_info())
        await responses.reply(ctx, embed)

    @commands.command(aliases=['q', 'show_queue', 'list', 'queue_list'])
    async def queue(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="queue", description="Shows the current music queue")
    async def queue_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Queue(bot))
