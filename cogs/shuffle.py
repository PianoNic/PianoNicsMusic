import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import responses


class Shuffle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        if not await db_utils.get_guild(ctx.guild.id):
            await responses.not_connected(ctx)
            return

        if await db_utils.shuffle_playlist(ctx.guild.id):
            await responses.confirm(ctx, "🔀", "Shuffle Enabled", "Now shuffling")
        else:
            await responses.confirm(ctx, "➡️", "Shuffle Disabled", "Shuffling disabled")

    @commands.command()
    async def shuffle(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="shuffle", description="Shuffeling of the queue")
    async def shuffle_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Shuffle(bot))
