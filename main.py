# Standard library imports
import asyncio
import base64
import io
import json
import os
import sys
import logging
import logging.handlers

# Third-party imports
import discord
import websockets
from discord.commands import Option, OptionChoice
from discord.ext import commands
from dotenv import load_dotenv
import configparser

# Local application imports
from db_utils.db import setup_db
import db_utils.db_utils as db_utils
from discord_utils import embed_generator, player
from discord_utils.dynamic_volume import set_guild_volume, adjust_guild_volume, get_guild_current_volume
from ai_server_utils import rvc_server_checker
from platform_handlers import music_url_getter
from ddl_retrievers.universal_ddl_retriever import YouTubeError
from utils import get_version, get_full_version_info, get_version_info
from utils.yt_dlp_updater import scheduled_update_check

load_dotenv()

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Get the original formatted message
        log_message = super().format(record)
        
        # Add color for the level name
        level_name = record.levelname
        if level_name in self.COLORS:
            # Replace the level name with colored version
            colored_level = f"{self.COLORS[level_name]}{level_name}{self.COLORS['RESET']}"
            log_message = log_message.replace(f"[{level_name}]", f"[{colored_level}]")
        
        return log_message

# Set up logging
def setup_logging():
    """Configure logging for the Discord bot"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure main discord logger
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    
    # Set HTTP logger to INFO to reduce noise
    logging.getLogger('discord.http').setLevel(logging.INFO)
    
    # Create rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        filename='logs/discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    
    # Also create a console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter('[{levelname}] {name}: {message}', style='{')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create application logger
    app_logger = logging.getLogger('PianoNicsMusic')
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(handler)
    app_logger.addHandler(console_handler)

    app_logger.propagate = False

    return app_logger

# Initialize logging
app_logger = setup_logging()

model_choices = []

# isServerRunning = rvc_server_pinger.check_connection()
# if(isServerRunning):
#     model_choices, index_choices = rvc_server_checker.fetch_choices()

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=[".", "!", "$"], intents=intents, help_command=None)

@bot.event
async def on_ready():
    await setup_db()
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Activity(type=discord.ActivityType.listening, name="to da kuhle songs"))
    if bot.user:
        app_logger.info(f"Bot is ready and logged in as {bot.user.name}")

    if not any(task.get_name() == 'yt-dlp-update-check' for task in asyncio.all_tasks()):
        app_logger.info("Starting yt-dlp update checker background task...")
        bot.loop.create_task(scheduled_update_check(), name='yt-dlp-update-check')

    ask_in_dms = config.getboolean('Bot', 'AskInDMs', fallback=False)
    admin_userid = config.getint('Admin', 'UserID', fallback=0)

    if ask_in_dms and admin_userid and bot.user:
        user = await bot.fetch_user(admin_userid)

        dm_channel = await user.create_dm()

        messages = await dm_channel.history().flatten()

        for msg in messages:
            try:
                await msg.delete()
            except Exception as e:
                app_logger.debug(f"Could not delete DM message: {e}")

        await user.send(f"Bot is ready and logged in as {bot.user.name}")
        app_logger.info(f"Sent ready notification to admin user {admin_userid}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Handle errors that occur during event processing"""
    app_logger.error(f"Error in event {event}", exc_info=True)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        # Don't log command not found errors
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        app_logger.warning(f"Missing argument in command {ctx.command}: {error}")
        try:
            await ctx.send(embed=await embed_generator.create_error_embed("Missing Argument", str(error)))
        except:
            pass
    elif isinstance(error, commands.BotMissingPermissions):
        app_logger.warning(f"Bot missing permissions: {error}")
        try:
            await ctx.send(embed=await embed_generator.create_error_embed("Missing Permissions", "The bot doesn't have the required permissions to execute this command."))
        except:
            pass
    else:
        app_logger.error(f"Unhandled command error in {ctx.command}: {error}", exc_info=True)
        try:
            await ctx.send(embed=await embed_generator.create_error_embed("Command Error", "An unexpected error occurred while executing this command."))
        except:
            pass

@bot.command(aliases=['next', 'advance', 'skip_song', 'move_on', 'play_next'])
async def skip(ctx):
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if voice_client:
            voice_client.stop() # type: ignore
        
            if ctx.message:
                await ctx.message.add_reaction("⏭️")
            else:
                await ctx.respond(embed=await embed_generator.create_success_embed("⏭️ Skipped", "Skipped Song"))
        else:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
    except Exception as e:
        app_logger.error(f"Error in skip command: {e}")
        try:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "An error occurred while skipping"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "An error occurred while skipping"))
        except Exception as send_error:
            app_logger.error(f"Failed to send error message: {send_error}")

@bot.command(aliases=['exit', 'quit', 'bye', 'farewell', 'goodbye', 'leave_now', 'disconnect', 'stop_playing'])
async def leave(ctx):
    try:
        voice_client = ctx.voice_client
        user_channel = ctx.author.voice.channel if ctx.author.voice else None
        bot_channel = voice_client.channel if voice_client else None

        if voice_client and bot_channel:
            if not user_channel or user_channel.id != bot_channel.id:
                if ctx.message:
                    await ctx.send(embed=await embed_generator.create_error_embed("Access Denied", f"Only users in `{bot_channel.name}` can disconnect the bot. Please join that channel to use this command."))
                else:
                    await ctx.respond(embed=await embed_generator.create_error_embed("Access Denied", f"Only users in `{bot_channel.name}` can disconnect the bot. Please join that channel to use this command."))
                return

        if voice_client:
            try:
                await db_utils.delete_queue(ctx.guild.id)
            except Exception as e:
                app_logger.error(f"Error deleting queue: {e}")
            
            try:
                voice_client.stop()
            except Exception as e:
                app_logger.error(f"Error stopping voice client: {e}")
            
            try:
                await voice_client.disconnect()
            except Exception as e:
                app_logger.error(f"Error disconnecting voice client: {e}")
        
            if ctx.message:
                await ctx.message.add_reaction("👋")
            else:
                await ctx.respond(embed=await embed_generator.create_success_embed("👋 Goodbye", "Left the channel"))
        else:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
    except Exception as e:
        app_logger.error(f"Error in leave command: {e}")
        try:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "An error occurred while leaving"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "An error occurred while leaving"))
        except Exception as send_error:
            app_logger.error(f"Failed to send error message: {send_error}")
    
@bot.command(aliases=['hold', 'freeze', 'break', 'wait', 'intermission'])
async def pause(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        
    if voice_client and hasattr(voice_client, 'pause'):
        voice_client.pause()  # type: ignore
    
        if ctx.message:
            await ctx.message.add_reaction("⏸️")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("⏸️ Paused", "Paused the music"))

    else:
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        else:
            await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))

@bot.command(aliases=['continue', 'unpause', 'proceed', 'restart', 'go', 'resume_playback'])
async def resume(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and hasattr(voice_client, 'resume'):
        voice_client.resume()  # type: ignore
    
        if ctx.message:
            await ctx.message.add_reaction("▶️")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("▶️ Resumed", "Resumed the music"))

    else:
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        else:
            await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))

@bot.command(aliases=['v', 'vol', 'sound'])
async def volume(ctx, *, level=None):
    """Set or get the current volume level (0-100)"""
    try:
        guild = await db_utils.get_guild(ctx.guild.id)
        if not guild:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            return

        if level is None:
            # Get current volume - try real-time first, then database
            current_volume_float = get_guild_current_volume(ctx.guild.id)
            if current_volume_float is None:
                current_volume_float = guild.volume
            
            current_volume = int(current_volume_float * 100)
            volume_bar = "█" * (current_volume // 10) + "░" * (10 - current_volume // 10)
            
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_embed("🔊 Current Volume", f"{current_volume}% [{volume_bar}]"))
            else:
                await ctx.respond(embed=await embed_generator.create_embed("🔊 Current Volume", f"{current_volume}% [{volume_bar}]"))
        else:
            # Set volume
            try:
                volume_level = int(level)
                if volume_level < 0 or volume_level > 100:
                    raise ValueError("Volume must be between 0 and 100")
                
                volume_float = volume_level / 100.0
                
                # Update database
                success = await db_utils.set_volume(ctx.guild.id, volume_float)
                
                # Update real-time volume if currently playing
                realtime_updated = set_guild_volume(ctx.guild.id, volume_float)
                
                if success:
                    volume_bar = "█" * (volume_level // 10) + "░" * (10 - volume_level // 10)
                    
                    status_text = f"Volume set to {volume_level}% [{volume_bar}]"
                    
                    if ctx.message:
                        await ctx.message.add_reaction("🔊")
                    else:
                        await ctx.respond(embed=await embed_generator.create_success_embed("🔊 Volume Set", status_text))
                else:
                    if ctx.message:
                        await ctx.send(embed=await embed_generator.create_error_embed("Error", "Failed to set volume"))
                    else:
                        await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Failed to set volume"))
                        
            except ValueError:
                if ctx.message:
                    await ctx.send(embed=await embed_generator.create_error_embed("Invalid Volume", "Please enter a number between 0 and 100"))
                else:
                    await ctx.respond(embed=await embed_generator.create_error_embed("Invalid Volume", "Please enter a number between 0 and 100"))
                    
    except Exception as e:
        app_logger.error(f"Error in volume command: {e}")
        try:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "An error occurred while setting volume"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "An error occurred while setting volume"))
        except Exception as send_error:
            app_logger.error(f"Failed to send error message: {send_error}")

@bot.command(aliases=['vol+', 'louder'])
async def volume_up(ctx):
    """Increase volume by 10%"""
    try:
        guild = await db_utils.get_guild(ctx.guild.id)
        if not guild:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            return

        # Try real-time adjustment first
        realtime_volume = adjust_guild_volume(ctx.guild.id, 0.1)
        
        # Update database
        new_volume = await db_utils.adjust_volume(ctx.guild.id, 0.1)
        
        # Use real-time volume if available, otherwise use database volume
        volume_to_display = realtime_volume if realtime_volume is not None else new_volume
        
        volume_level = int(volume_to_display * 100)
        volume_bar = "█" * (volume_level // 10) + "░" * (10 - volume_level // 10)
        
        status_text = f"Volume increased to {volume_level}% [{volume_bar}]"
        
        if ctx.message:
            await ctx.message.add_reaction("🔊")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("🔊 Volume Up", status_text))
            
    except Exception as e:
        app_logger.error(f"Error in volume_up command: {e}")
        try:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "An error occurred while adjusting volume"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "An error occurred while adjusting volume"))
        except Exception as send_error:
            app_logger.error(f"Failed to send error message: {send_error}")

@bot.command(aliases=['vol-', 'quieter'])
async def volume_down(ctx):
    """Decrease volume by 10%"""
    try:
        guild = await db_utils.get_guild(ctx.guild.id)
        if not guild:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
            return

        # Try real-time adjustment first
        realtime_volume = adjust_guild_volume(ctx.guild.id, -0.1)
        
        # Update database
        new_volume = await db_utils.adjust_volume(ctx.guild.id, -0.1)
        
        # Use real-time volume if available, otherwise use database volume
        volume_to_display = realtime_volume if realtime_volume is not None else new_volume
        
        volume_level = int(volume_to_display * 100)
        volume_bar = "█" * (volume_level // 10) + "░" * (10 - volume_level // 10)
        
        status_text = f"Volume decreased to {volume_level}% [{volume_bar}]"
        
        if ctx.message:
            await ctx.message.add_reaction("🔉")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("🔉 Volume Down", status_text))
            
    except Exception as e:
        app_logger.error(f"Error in volume_down command: {e}")
        try:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "An error occurred while adjusting volume"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "An error occurred while adjusting volume"))
        except Exception as send_error:
            app_logger.error(f"Failed to send error message: {send_error}")

@bot.command()
async def stop(ctx):
    await leave(ctx)

@bot.command(aliases=['lp', 'repeat', 'cycle', 'toggle_loop', 'toggle_repeat'])
async def loop(ctx):
    guild = await db_utils.get_guild(ctx.guild.id)

    if not guild:
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        else:
            await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        return
    
    is_looping = await db_utils.toggle_loop(ctx.guild.id)

    if is_looping:
        if ctx.message:
            await ctx.message.add_reaction("🔄")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("🔄 Loop Enabled", "Now looping the queue"))
    else:
        if ctx.message:
            await ctx.message.add_reaction("⏹️")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("⏹️ Loop Disabled", "Stopped looping the queue"))

@bot.command(aliases=['fp', 'forceplay', 'playforce'])
async def force_play(ctx, *, query=None, insta_skip=False):
    guild = await db_utils.get_guild(ctx.guild.id)
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not guild:
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        else:
            await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        return

    if (len(guild.queue) != 0) and voice_client and query:
        await db_utils.add_force_next_play_to_queue(ctx.guild.id, query)
    else:
        await ctx.send(embed=await embed_generator.create_error_embed("Error", "No song is currently playing"))
    
    if insta_skip and voice_client and hasattr(voice_client, 'stop'):
        if ctx.message:
            await ctx.message.add_reaction("⏭️")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("⏭️ Force Playing", "Force playing Song"))

        voice_client.stop()  # type: ignore
        
    else:
        if ctx.message:
            await ctx.message.add_reaction("📥")
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("📥 Queued", "Playing next up"))

@bot.command()
async def shuffle(ctx):
    guild = await db_utils.get_guild(ctx.guild.id)

    if not guild:
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        else:
            await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Bot is not connected to a Voice channel"))
        return

    shuffle_enabled = await db_utils.shuffle_playlist(ctx.guild.id)

    if ctx.message:
        if shuffle_enabled:
            await ctx.message.add_reaction("🔀")
        else:
            await ctx.message.add_reaction("➡️")
    else:
        if shuffle_enabled:
            await ctx.respond(embed=await embed_generator.create_success_embed("🔀 Shuffle Enabled", "Now shuffling"))
        else:
            await ctx.respond(embed=await embed_generator.create_success_embed("➡️ Shuffle Disabled", "Shuffling disabled"))

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    if ctx.message:
        await ctx.send(embed=await embed_generator.create_info_embed("🏓 Pong!", f"Latency is {latency}ms"))
    else:
        await ctx.respond(embed=await embed_generator.create_info_embed("🏓 Pong!", f"Latency is {latency}ms"))

@bot.command(aliases=['h', 'commands', 'command', 'cmds', 'cmd', 'info', 'assist', 'assistme', 'helpme', 'helppls', 'helpmepls', 'helpmeplease', 'helpmeout', 'helpmeoutpls', 'helpmeoutplease'])
async def help(ctx):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are all the available commands:",
        color=0x282841
    )    
    commands_list = [
        ("stop", "Stops the currently playing audio"),
        ("skip", "Skips the currently playing audio"),
        ("leave", "Leaves the voice channel and stops playing audio"),
        ("loop", "Toggles looping of the queue"),
        ("ping", "Checks the bot's latency"),
        ("pause", "Pauses the currently playing audio"),
        ("resume", "Resumes the currently paused audio"),
        ("volume", "Sets or shows the current volume (0-100)"),
        ("volume_up", "Increases volume by 10%"),
        ("volume_down", "Decreases volume by 10%"),
        ("force_play", "Force plays the provided audio"),
        ("play", "Plays the provided audio"),
        ("shuffle", "Shuffles the current music queue"),
        ("queue", "Shows the current music queue"),
        ("information", "Shows bot information and version"),
        ("bot_status", "Shows current bot and queue status"),
        #("play_with_ai_voice", "Plays the provided audio with custom AI voice")
    ]

    for name, description in commands_list:
        embed.add_field(name=f"/{name}", value=description, inline=False)

    embed.set_footer(text=get_full_version_info())

    if ctx.message:
        await ctx.send(embed=embed)
    else:
        await ctx.respond(embed=embed)

@bot.command(name='play', aliases=['p', 'pl', 'play_song', 'add', 'enqueue'])
async def play_command(ctx, *, query=None):

    # For application commands (slash commands), show "bot is thinking"
    # Only defer if the interaction hasn't been responded to yet
    if hasattr(ctx, 'defer') and not ctx.message and not ctx.response.is_done():
        await ctx.defer()

    if ctx.message and ctx.message.attachments and len(ctx.message.attachments) > 0:
        query = ctx.message.attachments[0].url

    if query is not None:
        try:
            song_urls = await music_url_getter.get_urls(query)
        except YouTubeError as e:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("YouTube Playlist Error", str(e)))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("YouTube Playlist Error", str(e)))
            return
        except Exception as e:
            app_logger.error(f"Error getting URLs for query {query}: {e}")
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "Failed to process your request. Please try again."))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "Failed to process your request. Please try again."))
            return
    else:
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_error_embed("Missing Input", "Please provide a query or attach a file."))
        else:
            await ctx.respond(embed=await embed_generator.create_error_embed("Missing Input", "Please provide a query or attach a file."))
        return

    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    user_voice = getattr(ctx.author, 'voice', None)
    user_channel = getattr(user_voice, 'channel', None)
    
    # Check if bot is already connected and user is in different channel
    if voice_client and voice_client.channel:
        if not user_channel or (hasattr(user_channel, 'id') and hasattr(voice_client.channel, 'id') and getattr(user_channel, 'id', None) != getattr(voice_client.channel, 'id', None)):
            channel_name = getattr(voice_client.channel, 'name', 'Unknown')
            error_msg = f"Bot is already playing music in another voice channel: `{channel_name}`. Please join that channel to queue music."
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Channel Conflict", error_msg))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Channel Conflict", error_msg))
            return

    guild = await db_utils.get_guild(ctx.guild.id)
    if not guild:
        await db_utils.create_new_guild(ctx.guild.id)
        guild = await db_utils.get_guild(ctx.guild.id)
        # Enhanced voice connection with error handling
        try:
            author_voice = getattr(ctx.author, 'voice', None)
            if not author_voice or not author_voice.channel:
                error_msg = "You must be in a voice channel to use this command!"
                if ctx.message:
                    await ctx.send(embed=await embed_generator.create_error_embed("Voice Channel Required", error_msg))
                else:
                    await ctx.respond(embed=await embed_generator.create_error_embed("Voice Channel Required", error_msg))
                return
            
            await author_voice.channel.connect()
            if hasattr(author_voice.channel, 'name'):
                app_logger.info(f"Successfully connected to voice channel: {author_voice.channel.name}")

        except discord.errors.ClientException as e:
            error_msg = "Failed to connect to voice channel. The bot might already be connected elsewhere."
            app_logger.warning(f"Voice connection error: {e}")
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Connection Failed", error_msg))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Connection Failed", error_msg))
            return
        
        except Exception as e:
            error_msg = "An error occurred while connecting to the voice channel. Please try again."
            app_logger.error(f"Unexpected voice connection error: {e}")
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Connection Error", error_msg))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Connection Error", error_msg))
            return
        
    isQueueEmpty = (await db_utils.get_queue_total_entries(ctx.guild.id)) == 0
    await db_utils.add_to_queue(ctx.guild.id, song_urls)
    
    queue_length = len(song_urls)
    if queue_length > 1:
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_embed("Queue", f"Added **{queue_length}** Songs to the Queue"))
        else:
            await ctx.respond(embed=await embed_generator.create_embed("Queue", f"Added **{queue_length}** Songs to the Queue"))

        if not isQueueEmpty:
            return
        
    elif queue_length == 1 and not isQueueEmpty:
        if ctx.message:
            await ctx.message.add_reaction("📥")
        else:
            try:
                await ctx.respond(embed=await embed_generator.create_success_embed("📥 Added", "Added to the queue"))
            except:
                await ctx.send(embed=await embed_generator.create_success_embed("📥 Added", "Added to the queue"))

        return
    
    try:
        while True:
            url = await db_utils.get_queue_entry(ctx.guild.id)

            if not url:
                break

            try:
                await player.play(ctx, url)
            except Exception as e:
                app_logger.error(f"Error playing song {url}: {e}")
                # Send error message to user and continue with next song
                try:
                    error_embed = await embed_generator.create_embed("Error", f"Failed to play a song. Skipping to next...")
                    if ctx.message:
                        await ctx.send(embed=error_embed)
                    else:
                        await ctx.respond(embed=error_embed)
                except Exception as send_error:
                    app_logger.error(f"Failed to send error message: {send_error}")
                continue  # Continue to next song instead of breaking
                
    except Exception as e:
        app_logger.critical(f"Critical error in play loop: {e}")
    finally:
        # Always cleanup, even if there was an error
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        
        if voice_client and hasattr(voice_client, 'disconnect'):
            try:
                await voice_client.disconnect()  # type: ignore
            except Exception as e:
                app_logger.error(f"Error disconnecting voice client: {e}")
            
        try:
            await db_utils.delete_guild(ctx.guild.id)
        except Exception as e:
            app_logger.error(f"Error cleaning up guild data: {e}")
            
@bot.command(name="information", aliases=['ver', 'version'])
async def information(ctx):
    try:
        version_info = get_version_info()
        version_embed = discord.Embed(
            title="🤖 Bot Version Information",
            color=0x282841
        )
        
        version_embed.add_field(
            name="Current Version", 
            value=f"`{version_info['version']}`", 
            inline=True
        )
        
        version_embed.add_field(
            name="Release Date", 
            value=f"`{version_info['release_date']}`", 
            inline=True
        )
        
        version_embed.add_field(
            name="Created By", 
            value=f"{version_info['author']}", 
            inline=True
        )
        
        version_embed.add_field(
            name="Python Version", 
            value=f"`{sys.version.split()[0]}`", 
            inline=True
        )
        
        version_embed.add_field(
            name="Discord.py Version", 
            value=f"`{discord.__version__}`", 
            inline=True
        )
        
        version_embed.add_field(
            name="📊 Bot Statistics", 
            value=f"Servers: `{len(bot.guilds)}`\nLatency: `{round(bot.latency * 1000)}ms`", 
            inline=True
        )
        
        version_embed.set_footer(text=get_full_version_info())
        
        if ctx.message:
            await ctx.send(embed=version_embed)
        else:
            await ctx.respond(embed=version_embed)
    except Exception as e:
        app_logger.error(f"Error in version command: {e}")
        # Fallback to simple version display
        if ctx.message:
            await ctx.send(embed=await embed_generator.create_info_embed("Bot Version", f"PianoNics-Music v{get_version()}"))
        else:
            await ctx.respond(embed=await embed_generator.create_info_embed("Bot Version", f"PianoNics-Music v{get_version()}"))

###################################################
################# SLASH COMMANDS ##################
###################################################

@bot.slash_command(name="information", description="Gets the Bot information")
async def information_slash(ctx):
    await information(ctx)

@bot.slash_command(name="skip", description="Skips the currently playing audio")
async def skip_slash(ctx):
    await skip(ctx)

@bot.slash_command(name="leave", description="Leaves the voice channel and stops playing audio")
async def leave_slash(ctx):
    await leave(ctx)

@bot.slash_command(name="stop", description="Stops playing audio")
async def stop_slash(ctx):
    await stop(ctx)

@bot.slash_command(name="loop", description="Toggles looping of the queue")
async def loop_slash(ctx):
    await loop(ctx)

@bot.slash_command(name="shuffle", description="Shuffeling of the queue")
async def shuffle_slash(ctx):
    await shuffle(ctx)

@bot.slash_command(name="ping", description="Checks the bot's latency")
async def ping_slash(ctx):
    await ping(ctx)

@bot.slash_command(name="pause", description="Pauses the currently playing audio")
async def pause_slash(ctx):
    await pause(ctx)

@bot.slash_command(name="resume", description="Resumes the currently paused audio")
async def resume_slash(ctx):
    await resume(ctx)

@bot.slash_command(
    name="force_play",
    description="Force plays the provided audio",
    options=[
        Option(
            name="query",
            description="The audio track to play",
            required=True,
            type=str,
        ),
        Option(
            name="insta_skip",
            description="Skip to the next track immediately",
            required=False,
            choices=[
                OptionChoice(name="Yes", value="true"),
                OptionChoice(name="No", value="false")
            ],
            type=str,
        ),
    ]
)
async def force_play_slash(ctx, query: str, insta_skip: str = "false"):
    insta_skip_bool = insta_skip == "true"
    await force_play(ctx, query=query, insta_skip=insta_skip_bool)

@bot.slash_command(name="help", description="Shows all available commands")
async def help_slash(ctx):
    await help(ctx)

@bot.slash_command(name="bot_status", description="Shows current bot and queue status")
async def bot_status_slash(ctx):
    await bot_status(ctx)

@bot.slash_command(name="play", description="Plays the provided audio")
async def play_slash(ctx, query: str = None, file: discord.Attachment = None):
    # Show "bot is thinking" for slash commands
    await ctx.defer()
    
    if query and file:
        await ctx.respond(embed=await embed_generator.create_error_embed("Invalid Input", "Please provide either a query OR a file, not both."), ephemeral=True)
        return
    
    if not query and not file:
        await ctx.respond(embed=await embed_generator.create_error_embed("Missing Input", "Please provide either a query or attach a file."), ephemeral=True)
        return
    
    if file:
        query = file.url

    await play_command(ctx, query=query)

@bot.slash_command(name="queue", description="Shows the current music queue")
async def queue_slash(ctx):
    await queue(ctx)

@bot.slash_command(name="volume", description="Sets or shows the current volume (0-100)")
async def volume_slash(ctx, level: int = None):
    await volume(ctx, level=level)

@bot.slash_command(name="volume_up", description="Increases volume by 10%")
async def volume_up_slash(ctx):
    await volume_up(ctx)

@bot.slash_command(name="volume_down", description="Decreases volume by 10%")
async def volume_down_slash(ctx):
    await volume_down(ctx)

# if isServerRunning:
#     @bot.slash_command(
#         name="play_with_ai_voice",
#         description="A command to play with custom voice",
#         options=[
#             Option(  
#                 name="model",
#                 description="Choose a model",
#                 required=True,
#                 choices=[OptionChoice(name=choice, value=choice) for choice in model_choices],
#             ),
#             Option(
#                 name="index",
#                 description="Choose an index",
#                 required=True,
#                 choices=[OptionChoice(name=choice, value=choice) for choice in index_choices],
#             ),
#             Option(
#                 name="pitch",
#                 description="Enter a pitch",
#                 required=True,
#                 choices=[
#                     OptionChoice(name="↑12", value="12"),
#                     OptionChoice(name="↑6", value="6"),
#                     OptionChoice(name="0", value="0"),
#                     OptionChoice(name="↓6", value="-6"),
#                     OptionChoice(name="↓12", value="-12")
#                 ],
#                 type=int,
#             ),
#             Option(
#                 name="url",
#                 description="Enter a URL",
#                 required=True,
#                 type=str,
#             ),
#         ],
#     )
#     async def play_with_custom_voice(ctx, model: str, index: str, pitch: int, url: str):
#         async with websockets.connect('ws://localhost:8765', max_size=26_000_000) as websocket:
#             request_data = {
#                 "command": "generate_ai_cover",
#                 "model": model,
#                 "index": index,
#                 "pitch": pitch,
#                 "url": url
#             }
            
#             await websocket.send(json.dumps(request_data))
#             print(json.dumps(request_data))

#             message = await websocket.recv()
#             data = json.loads(message)

#             dc_message = await ctx.respond(embed=await embed_generator.create_embed("🗣️ AI Singer 🗣️", data["message"]))

#             # Listen for updates from the server
#             while True:
#                 message = await websocket.recv()
#                 data = json.loads(message)
#                 #print(data)
#                 if "message" in data:
#                     # Send a new message with the update
#                     await dc_message.edit(embed=await embed_generator.create_embed("AI Singer", data["message"]))
#                 elif "file" in data:
#                     file_data = base64.b64decode(data["file"])
#                     file_like_object = io.BytesIO(file_data)
#                     edited_message = await dc_message.edit(embed=await embed_generator.create_embed("AI Singer", "Finished"), file=discord.File(file_like_object, filename="unknown.mp3"))
#                     file_url = edited_message.attachments[0].url

#                     await play_command(ctx, query=file_url)
#                 elif "error" in data:
#                     await dc_message.edit(f"Error from server: {data['error']}")
#                 elif "queue_position" in data:
#                     await dc_message.edit(embed=await embed_generator.create_embed("AI Singer", f"Your request is at position {data['queue_position']} in the queue."))
#                 elif "status" in data:
#                     print("made it out")
#                     break

#         print("finished")

@bot.command(aliases=['status', 'current', 'now_playing'])
async def bot_status(ctx):
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        guild = await db_utils.get_guild(ctx.guild.id)
        
        status_embed = discord.Embed(
            title="🎵 Bot Status",
            color=0x282841
        )
        
        # Voice connection status
        if voice_client and hasattr(voice_client, 'is_connected') and voice_client.is_connected():  # type: ignore
            channel_name = getattr(voice_client.channel, 'name', 'Unknown') if voice_client.channel else "Unknown"
            status_embed.add_field(
                name="🔊 Voice Status", 
                value=f"Connected to: `{channel_name}`", 
                inline=True
            )
            
            # Playing status
            if hasattr(voice_client, 'is_playing') and voice_client.is_playing():  # type: ignore
                status_embed.add_field(name="▶️ Playback", value="Playing", inline=True)
            elif hasattr(voice_client, 'is_paused') and voice_client.is_paused():  # type: ignore
                status_embed.add_field(name="⏸️ Playback", value="Paused", inline=True)
            else:
                status_embed.add_field(name="⏹️ Playback", value="Stopped", inline=True)
        else:
            status_embed.add_field(name="🔇 Voice Status", value="Not connected", inline=True)
            status_embed.add_field(name="⏹️ Playback", value="Inactive", inline=True)
        
        # Queue information
        if guild:
            queue_count = len([entry for entry in guild.queue if not entry.already_played])
            total_queue = len(guild.queue)
            
            status_embed.add_field(
                name="📝 Queue", 
                value=f"{queue_count} remaining / {total_queue} total", 
                inline=True
            )            # Loop, shuffle, and volume status
            loop_status = "🔄 On" if guild.loop_queue else "⏹️ Off"
            shuffle_status = "🔀 On" if guild.shuffle_queue else "➡️ Off"
            
            # Get real-time volume if available, otherwise use database volume
            current_volume_float = get_guild_current_volume(ctx.guild.id)
            if current_volume_float is None:
                current_volume_float = guild.volume
            volume_status = f"🔊 {int(current_volume_float * 100)}%"
            
            status_embed.add_field(name="Loop", value=loop_status, inline=True)
            status_embed.add_field(name="Shuffle", value=shuffle_status, inline=True)
            status_embed.add_field(name="Volume", value=volume_status, inline=True)
        else:
            status_embed.add_field(name="📝 Queue", value="No active session", inline=True)
            status_embed.add_field(name="Loop", value="⏹️ Off", inline=True)
            status_embed.add_field(name="Shuffle", value="➡️ Off", inline=True)
            status_embed.add_field(name="Volume", value="🔊 100%", inline=True)
          # Server info
        latency = round(bot.latency * 1000)
        status_embed.add_field(name="📡 Latency", value=f"{latency}ms", inline=True)
        
        status_embed.set_footer(text=get_full_version_info())
        
        if ctx.message:
            await ctx.send(embed=status_embed)
        else:
            await ctx.respond(embed=status_embed)
            
    except Exception as e:
        app_logger.error(f"Error in status command: {e}")
        try:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "An error occurred while getting status"))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "An error occurred while getting status"))
        except Exception as send_error:
            app_logger.error(f"Failed to send error message: {send_error}")

@bot.command(aliases=['q', 'show_queue', 'list', 'queue_list'])
async def queue(ctx):
    try:
        guild = await db_utils.get_guild(ctx.guild.id)
        if not guild or not guild.queue:
            embed = discord.Embed(
                title="🎶 Queue",
                description="The queue is currently empty.",
                color=0x282841
            )
        else:
            queue_entries = [entry for entry in guild.queue if not getattr(entry, 'already_played', False)]
            now_playing = next((entry for entry in guild.queue if getattr(entry, 'already_played', False)), None)
            embed = discord.Embed(
                title="🎶 Current Queue",
                color=0x282841
            )
            if now_playing:
                embed.add_field(name="Now Playing", value=f"[{getattr(now_playing, 'title', 'Unknown')}]({getattr(now_playing, 'url', 'N/A')})", inline=False)
            if queue_entries:
                for idx, entry in enumerate(queue_entries[:10], start=1):
                    embed.add_field(
                        name=f"#{idx}",
                        value=f"[{getattr(entry, 'title', 'Unknown')}]({getattr(entry, 'url', 'N/A')})",
                        inline=False
                    )
                if len(queue_entries) > 10:
                    embed.add_field(name="...", value=f"And {len(queue_entries) - 10} more...", inline=False)
            else:
                embed.add_field(name="Up Next", value="No more songs in the queue.", inline=False)
            embed.set_footer(text=get_full_version_info())
        if ctx.message:
            await ctx.send(embed=embed)
        else:
            await ctx.respond(embed=embed)
    except Exception as e:
        app_logger.error(f"Error in queue command: {e}")
        try:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_error_embed("Error", "An error occurred while getting the queue."))
            else:
                await ctx.respond(embed=await embed_generator.create_error_embed("Error", "An error occurred while getting the queue."))
        except Exception as send_error:
            app_logger.error(f"Failed to send error message: {send_error}")

bot.run(os.getenv('DISCORD_TOKEN'))
