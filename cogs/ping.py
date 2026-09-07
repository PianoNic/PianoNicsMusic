import discord
from discord.ext import commands

from discord_utils import embed_generator, responses


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        latency = round(self.bot.latency * 1000)
        await responses.reply(ctx, await embed_generator.create_info_embed("🏓 Pong!", f"Latency is {latency}ms"))

    @commands.command()
    async def ping(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="ping", description="Checks the bot's latency")
    async def ping_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Ping(bot))
