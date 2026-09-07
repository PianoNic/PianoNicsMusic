import logging

import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import embed_generator, meters, responses
from discord_utils.dynamic_bass_boost import get_guild_current_bass_boost, set_guild_bass_boost

logger = logging.getLogger('PianoNicsMusic')

STEP = 20


class BassBoost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx, level):
        guild = await db_utils.get_guild(ctx.guild.id)

        if not guild:
            await responses.not_connected(ctx)
            return

        if level is None:
            current = get_guild_current_bass_boost(ctx.guild.id)
            if current is None:
                current = guild.bass_boost

            percent = int(current * 100)
            await responses.reply(
                ctx,
                await embed_generator.create_embed(
                    "🎸 Current Bass Boost", f"{percent}% [{meters.bar(percent, STEP)}]"
                ),
            )
            return

        try:
            percent = int(level)
        except (TypeError, ValueError):
            await responses.fail(ctx, "Invalid Bass Boost", "Please enter a number between 0 and 200")
            return

        if not 0 <= percent <= 200:
            await responses.fail(ctx, "Invalid Bass Boost", "Please enter a number between 0 and 200")
            return

        if not await db_utils.set_bass_boost(ctx.guild.id, percent / 100.0):
            await responses.fail(ctx, "Error", "Failed to set bass boost")
            return

        set_guild_bass_boost(ctx.guild.id, percent / 100.0)
        await responses.confirm(
            ctx, "🎸", "Bass Boost Set", f"Bass boost set to {percent}% [{meters.bar(percent, STEP)}]"
        )

    @commands.command(aliases=['bass', 'b', 'lowend'])
    async def bass_boost(self, ctx, *, level=None):
        await self.run(ctx, level)

    @discord.slash_command(name="bass_boost", description="Sets or shows the bass boost (0-200)")
    async def bass_boost_slash(self, ctx, level: int = None):
        await self.run(ctx, level)


def setup(bot):
    bot.add_cog(BassBoost(bot))
