import logging

import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import responses

logger = logging.getLogger('PianoNicsMusic')


async def leave_voice(ctx):
    voice_client = ctx.voice_client

    if not voice_client:
        await responses.not_connected(ctx)
        return

    bot_channel = voice_client.channel
    user_channel = ctx.author.voice.channel if ctx.author.voice else None

    if bot_channel and (not user_channel or user_channel.id != bot_channel.id):
        await responses.fail(
            ctx,
            "Access Denied",
            f"Only users in `{bot_channel.name}` can disconnect the bot. Please join that channel to use this command.",
        )
        return

    try:
        await db_utils.delete_queue(ctx.guild.id)
    except Exception as error:
        logger.error(f"Error deleting queue: {error}")

    try:
        voice_client.stop()
        await voice_client.disconnect()
    except Exception as error:
        logger.error(f"Error disconnecting voice client: {error}")

    await responses.confirm(ctx, "👋", "Goodbye", "Left the channel")


class Leave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['exit', 'quit', 'bye', 'farewell', 'goodbye', 'leave_now', 'disconnect', 'stop_playing'])
    async def leave(self, ctx):
        await leave_voice(ctx)

    @discord.slash_command(name="leave", description="Leaves the voice channel and stops playing audio")
    async def leave_slash(self, ctx):
        await leave_voice(ctx)


def setup(bot):
    bot.add_cog(Leave(bot))
