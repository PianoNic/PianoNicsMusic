import logging

import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import embed_generator, meters, responses
from discord_utils.dynamic_volume import get_guild_current_volume, set_guild_volume

logger = logging.getLogger('PianoNicsMusic')


class Volume(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx, level):
        guild = await db_utils.get_guild(ctx.guild.id)

        if not guild:
            await responses.not_connected(ctx)
            return

        if level is None:
            current = get_guild_current_volume(ctx.guild.id)
            if current is None:
                current = guild.volume

            percent = int(current * 100)
            await responses.reply(
                ctx,
                await embed_generator.create_embed("🔊 Current Volume", f"{percent}% [{meters.bar(percent)}]"),
            )
            return

        try:
            percent = int(level)
        except (TypeError, ValueError):
            await responses.fail(ctx, "Invalid Volume", "Please enter a number between 0 and 100")
            return

        if not 0 <= percent <= 100:
            await responses.fail(ctx, "Invalid Volume", "Please enter a number between 0 and 100")
            return

        if not await db_utils.set_volume(ctx.guild.id, percent / 100.0):
            await responses.fail(ctx, "Error", "Failed to set volume")
            return

        set_guild_volume(ctx.guild.id, percent / 100.0)
        await responses.confirm(ctx, "🔊", "Volume Set", f"Volume set to {percent}% [{meters.bar(percent)}]")

    @commands.command(aliases=['v', 'vol', 'sound'])
    async def volume(self, ctx, *, level=None):
        await self.run(ctx, level)

    @discord.slash_command(name="volume", description="Sets or shows the current volume (0-100)")
    async def volume_slash(self, ctx, level: int = None):
        await self.run(ctx, level)


def setup(bot):
    bot.add_cog(Volume(bot))
