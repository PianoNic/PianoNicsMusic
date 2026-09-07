import logging
import sys

import discord
from discord.ext import commands

from discord_utils import embed_generator, responses
from utils import get_full_version_info, get_version, get_version_info

logger = logging.getLogger('PianoNicsMusic')


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        try:
            info = get_version_info()

            embed = discord.Embed(title="🤖 Bot Version Information", color=0x282841)
            embed.add_field(name="Current Version", value=f"`{info['version']}`", inline=True)
            embed.add_field(name="Release Date", value=f"`{info['release_date']}`", inline=True)
            embed.add_field(name="Created By", value=f"{info['author']}", inline=True)
            embed.add_field(name="Python Version", value=f"`{sys.version.split()[0]}`", inline=True)
            embed.add_field(name="Pycord Version", value=f"`{discord.__version__}`", inline=True)
            embed.add_field(
                name="📊 Bot Statistics",
                value=f"Servers: `{len(self.bot.guilds)}`\nLatency: `{round(self.bot.latency * 1000)}ms`",
                inline=True,
            )
            embed.set_footer(text=get_full_version_info())

            await responses.reply(ctx, embed)
        except Exception as error:
            logger.error(f"Error in information command: {error}")
            await responses.reply(
                ctx, await embed_generator.create_info_embed("Bot Version", f"PianoNics-Music v{get_version()}")
            )

    @commands.command(name="information", aliases=['ver', 'version'])
    async def information(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="information", description="Gets the Bot information")
    async def information_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(Information(bot))
