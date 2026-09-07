import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import meters, responses
from discord_utils.dynamic_bass_boost import adjust_guild_bass_boost

STEP = -0.1


class BassBoostDown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        if not await db_utils.get_guild(ctx.guild.id):
            await responses.not_connected(ctx)
            return

        realtime = adjust_guild_bass_boost(ctx.guild.id, STEP)
        stored = await db_utils.adjust_bass_boost(ctx.guild.id, STEP)

        percent = int((realtime if realtime is not None else stored) * 100)
        await responses.confirm(
            ctx, "🎸", "Bass Boost Down", f"Bass boost decreased to {percent}% [{meters.bar(percent, 20)}]"
        )

    @commands.command(aliases=['bass-', 'bassdown', 'less_bass'])
    async def bass_boost_down(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="bass_boost_down", description="Decreases bass boost by 10%")
    async def bass_boost_down_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(BassBoostDown(bot))
