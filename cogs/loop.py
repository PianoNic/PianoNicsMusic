import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import responses


class Loop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        if not await db_utils.get_guild(ctx.guild.id):
            await responses.not_connected(ctx)
            return

        if await db_utils.toggle_loop(ctx.guild.id):
            await responses.confirm(ctx, "🔄", "Loop Enabled", "Now looping the queue")
        else:
            await responses.confirm(ctx, "⏹️", "Loop Disabled", "Stopped looping the queue")

    @commands.command(aliases=['lp', 'repeat', 'cycle', 'toggle_loop', 'toggle_repeat'])
    async def loop(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="loop", description="Toggles looping of the queue")
    async def loop_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Loop(bot))
