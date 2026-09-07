import configparser
import logging

from discord.ext import commands

from db_utils.db import setup_db
from discord_utils import embed_generator

logger = logging.getLogger('PianoNicsMusic')


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

    @commands.Cog.listener()
    async def on_ready(self):
        import discord

        await setup_db()
        await self.bot.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Activity(type=discord.ActivityType.listening, name="to da kuhle songs"),
        )

        if self.bot.user:
            logger.info(f"Bot is ready and logged in as {self.bot.user.name}")

        await self.notify_admin()

    async def notify_admin(self):
        ask_in_dms = self.config.getboolean('Bot', 'AskInDMs', fallback=False)
        admin_userid = self.config.getint('Admin', 'UserID', fallback=0)

        if not (ask_in_dms and admin_userid and self.bot.user):
            return

        user = await self.bot.fetch_user(admin_userid)
        dm_channel = await user.create_dm()

        for message in await dm_channel.history().flatten():
            try:
                await message.delete()
            except Exception as error:
                logger.debug(f"Could not delete DM message: {error}")

        await user.send(f"Bot is ready and logged in as {self.bot.user.name}")
        logger.info(f"Sent ready notification to admin user {admin_userid}")

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        logger.error(f"Error in event {event}", exc_info=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            logger.warning(f"Missing argument in command {ctx.command}: {error}")
            title, message = "Missing Argument", str(error)
        elif isinstance(error, commands.BotMissingPermissions):
            logger.warning(f"Bot missing permissions: {error}")
            title, message = "Missing Permissions", "The bot doesn't have the required permissions to execute this command."
        else:
            logger.error(f"Unhandled command error in {ctx.command}: {error}", exc_info=True)
            title, message = "Command Error", "An unexpected error occurred while executing this command."

        try:
            await ctx.send(embed=await embed_generator.create_error_embed(title, message))
        except Exception as send_error:
            logger.debug(f"Could not report command error: {send_error}")


def setup(bot):
    bot.add_cog(Events(bot))
