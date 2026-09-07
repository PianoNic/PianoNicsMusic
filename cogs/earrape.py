import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import responses
from discord_utils.dynamic_earrape import toggle_guild_earrape


class Earrape(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        if not await db_utils.get_guild(ctx.guild.id):
            await responses.not_connected(ctx)
            return

        enabled = await db_utils.toggle_earrape(ctx.guild.id)
        toggle_guild_earrape(ctx.guild.id)

        if enabled:
            await responses.confirm(ctx, "📢", "Earrape", "Earrape enabled")
        else:
            await responses.confirm(ctx, "🔇", "Earrape", "Earrape disabled")

    @commands.command(aliases=['ear', 'rape', 'er'])
    async def earrape(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="earrape", description="Toggles the earrape filter")
    async def earrape_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Earrape(bot))
