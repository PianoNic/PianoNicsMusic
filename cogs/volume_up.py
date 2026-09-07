import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import meters, responses
from discord_utils.dynamic_volume import adjust_guild_volume

STEP = 0.1


class VolumeUp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        if not await db_utils.get_guild(ctx.guild.id):
            await responses.not_connected(ctx)
            return

        realtime = adjust_guild_volume(ctx.guild.id, STEP)
        stored = await db_utils.adjust_volume(ctx.guild.id, STEP)

        percent = int((realtime if realtime is not None else stored) * 100)
        await responses.confirm(ctx, "🔊", "Volume Up", f"Volume increased to {percent}% [{meters.bar(percent)}]")

    @commands.command(aliases=['vol+', 'louder'])
    async def volume_up(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="volume_up", description="Increases volume by 10%")
    async def volume_up_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(VolumeUp(bot))
