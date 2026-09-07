import discord
from discord.ext import commands

from cogs.leave import leave_voice


class Stop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stop(self, ctx):
        await leave_voice(ctx)

    @discord.slash_command(name="stop", description="Stops playing audio")
    async def stop_slash(self, ctx):
        await leave_voice(ctx)


def setup(bot):
    bot.add_cog(Stop(bot))
