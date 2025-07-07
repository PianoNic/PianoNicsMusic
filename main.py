# Standard library imports
import base64
import io
import json
import os
import sys
import logging

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
from ai_server_utils import rvc_server_checker
from platform_handlers import music_url_getter
from utils import get_version, get_full_version_info, get_version_info

load_dotenv()

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

model_choices = []

# isServerRunning = rvc_server_pinger.check_connection()
# if(isServerRunning):
#     model_choices, index_choices = rvc_server_checker.fetch_choices()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=[".", "!", "$"], intents=intents, help_command=None)

@bot.event
async def on_ready():
    await setup_db()
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Activity(type=discord.ActivityType.listening, name="to da kuhle songs"))
    print(f"Bot is ready and logged in as {bot.user.name}")
    
    ask_in_dms = config.getboolean('Bot', 'AskInDMs', fallback=False)
    admin_userid = config.getint('Admin', 'UserID', fallback=0)
    
    if ask_in_dms and admin_userid:
        user = await bot.fetch_user(admin_userid)
        
        dm_channel = await user.create_dm()
        
        messages = await dm_channel.history().flatten()
        
        for msg in messages:
            try:
                await msg.delete()
            except:
                print("skipped message")

        await user.send(f"Bot is ready and logged in as {bot.user.name}")

@bot.command(aliases=['next', 'advance', 'skip_song', 'move_on', 'play_next'])
async def skip(ctx):
    try:
        voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if voice_client:
            voice_client.stop()
        
            if ctx.message:
                await ctx.message.add_reaction("⏭️")
            else:
                await ctx.respond("Skipped Song ⏭️")
        else:
            if ctx.message:
                await ctx.send("❗ Bot is not connected to a Voice channel")
            else:
                await ctx.respond("❗ Bot is not connected to a Voice channel")
    except Exception as e:
        print(f"Error in skip command: {e}")
        try:
            if ctx.message:
                await ctx.send("❗ An error occurred while skipping")
            else:
                await ctx.respond("❗ An error occurred while skipping")
        except:
            pass

@bot.command(aliases=['exit', 'quit', 'bye', 'farewell', 'goodbye', 'leave_now', 'disconnect', 'stop_playing'])
async def leave(ctx):
    try:
        voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if voice_client:
            try:
                await db_utils.delete_queue(ctx.guild.id)
            except Exception as e:
                print(f"Error deleting queue: {e}")
            
            try:
                voice_client.stop()
            except Exception as e:
                print(f"Error stopping voice client: {e}")
            
            try:
                await voice_client.disconnect()
            except Exception as e:
                print(f"Error disconnecting voice client: {e}")
        
            if ctx.message:
                await ctx.message.add_reaction("👋")
            else:
                await ctx.respond("Left the channel 👋")
        else:
            if ctx.message:
                await ctx.send("❗ Bot is not connected to a Voice channel")
            else:
                await ctx.respond("❗ Bot is not connected to a Voice channel")
    except Exception as e:
        print(f"Error in leave command: {e}")
        try:
            if ctx.message:
                await ctx.send("❗ An error occurred while leaving")
            else:
                await ctx.respond("❗ An error occurred while leaving")
        except:
            pass
    
@bot.command(aliases=['hold', 'freeze', 'break', 'wait', 'intermission'])
async def pause(ctx):
    voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        
    if voice_client:
        voice_client.pause()
    
        if ctx.message:
            await ctx.message.add_reaction("⏸️")
        else:
            await ctx.respond("Paued the music ⏸️")

    else:
        if ctx.message:
            await ctx.send("❗ Bot is not connected to a Voice channel")
        else:
            await ctx.respond("❗ Bot is not connected to a Voice channel")

@bot.command(aliases=['continue', 'unpause', 'proceed', 'restart', 'go', 'resume_playback'])
async def resume(ctx):
    voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client:
        voice_client.resume()
    
        if ctx.message:
            await ctx.message.add_reaction("▶️")
        else:
            await ctx.respond("Resumed the music ▶️")

    else:
        if ctx.message:
            await ctx.send("❗ Bot is not connected to a Voice channel")
        else:
            await ctx.respond("❗ Bot is not connected to a Voice channel")

@bot.command()
async def stop(ctx):
    await leave(ctx)

@bot.command(aliases=['lp', 'repeat', 'cycle', 'toggle_loop', 'toggle_repeat'])
async def loop(ctx):
    guild = await db_utils.get_guild(ctx.guild.id)

    if not guild:
        if ctx.message:
            await ctx.send("❗ Bot is not connected to a Voice channel")
        else:
            await ctx.respond("❗ Bot is not connected to a Voice channel")
        return
    
    is_looping = await db_utils.toggle_loop(ctx.guild.id)

    if is_looping:
        if ctx.message:
            await ctx.message.add_reaction("🔄")
        else:
            await ctx.respond("Now looping the queue 🔄")
    else:
        if ctx.message:
            await ctx.message.add_reaction("⏹️")
        else:
            await ctx.respond("Stopped looping the queue ⏹️")

@bot.command(aliases=['fp', 'forceplay', 'playforce'])
async def force_play(ctx, *, query=None, insta_skip=False):
    guild = await db_utils.get_guild(ctx.guild.id)
    voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not guild:
        if ctx.message:
            await ctx.send("❗ Bot is not connected to a Voice channel")
        else:
            await ctx.respond("❗ Bot is not connected to a Voice channel")
        return

    if (len(guild.queue) != 0) and voice_client:
        await db_utils.add_force_next_play_to_queue(ctx.guild.id, query)
    else:
        await ctx.send("No song is currently playing")
    
    if insta_skip:
        if ctx.message:
            await ctx.message.add_reaction("⏭️")
        else:
            await ctx.respond("Force playing Song ⏭️")

        voice_client.stop()
        
    else:
        if ctx.message:
            await ctx.message.add_reaction("📥")
        else:
            await ctx.respond("Playing next up 📥")

@bot.command()
async def shuffle(ctx):
    guild = await db_utils.get_guild(ctx.guild.id)

    if not guild:
        if ctx.message:
            await ctx.send("❗ Bot is not connected to a Voice channel")
        else:
            await ctx.respond("❗ Bot is not connected to a Voice channel")
        return

    shuffle_enabled = await db_utils.shuffle_playlist(ctx.guild.id)

    if ctx.message:
        if shuffle_enabled:
            await ctx.message.add_reaction("🔀")
        else:
            await ctx.message.add_reaction("➡️")
    else:
        if shuffle_enabled:
            await ctx.respond("Now shuffling 🔀")
        else:
            await ctx.respond("Shuffling disabled ➡️")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    if ctx.message:
        await ctx.send(f'Pong! Latency is {latency}ms')
    else:
        await ctx.respond(f'Pong! Latency is {latency}ms')

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
        ("resume", "Resumes the currently paused audio"),        ("force_play", "Force plays the provided audio"),
        ("play", "Plays the provided audio"),        ("shuffle", "Shuffles the current music queue"),
        ("play_file", "Plays music from a file containing a list of URLs"),
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

@bot.command(name='play', aliases=['p', 'pl', 'play_song', 'queue', 'add', 'enqueue'])
async def play_command(ctx: discord.ApplicationContext, *, query=None):
    guild = await db_utils.get_guild(ctx.guild.id)

    song_urls = await music_url_getter.get_urls(query)
    await db_utils.add_to_queue(ctx.guild.id, song_urls)
    
    if guild:
        queue_length = len(song_urls)

        if queue_length > 1:
            if ctx.message:
                await ctx.send(embed=await embed_generator.create_embed("Queue", f"Added **{queue_length}** Songs to the Queue"))
            else:
                await ctx.respond(embed=await embed_generator.create_embed("Queue", f"Added **{queue_length}** Songs to the Queue"))

        else:
            if ctx.message:
                await ctx.message.add_reaction("📥")
            else:
                await ctx.respond("Added to the queue 📥")
        
        return
    else:
        await db_utils.create_new_guild(ctx.guild.id)
        
        # Enhanced voice connection with error handling
        try:
            if not ctx.author.voice or not ctx.author.voice.channel:
                error_msg = "❗ You must be in a voice channel to use this command!"
                if ctx.message:
                    await ctx.send(error_msg)
                else:
                    await ctx.respond(error_msg)
                return
            
            await ctx.author.voice.channel.connect()
            print(f"Successfully connected to voice channel: {ctx.author.voice.channel.name}")
            
        except discord.errors.ClientException as e:
            error_msg = "❗ Failed to connect to voice channel. The bot might already be connected elsewhere."
            print(f"Voice connection error: {e}")
            if ctx.message:
                await ctx.send(error_msg)
            else:
                await ctx.respond(error_msg)
            return
            
        except Exception as e:
            error_msg = "❗ An error occurred while connecting to the voice channel. Please try again."
            print(f"Unexpected voice connection error: {e}")
            if ctx.message:
                await ctx.send(error_msg)
            else:
                await ctx.respond(error_msg)
            return
    try:
        while True:
            url = await db_utils.get_queue_entry(ctx.guild.id)

            if not url:
                break

            try:
                await player.play(ctx, url)
            except Exception as e:
                print(f"Error playing song {url}: {e}")
                # Send error message to user and continue with next song
                try:
                    error_embed = await embed_generator.create_embed("Error", f"Failed to play a song. Skipping to next...")
                    if ctx.message:
                        await ctx.send(embed=error_embed)
                    else:
                        await ctx.respond(embed=error_embed)
                except:
                    pass  # If we can't send the error message, continue anyway
                continue  # Continue to next song instead of breaking
                
    except Exception as e:
        print(f"Critical error in play loop: {e}")
    finally:
        # Always cleanup, even if there was an error
        voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        
        if voice_client:
            try:
                await voice_client.disconnect()
            except:
                pass  # Ignore disconnect errors
            
        try:
            await db_utils.delete_guild(ctx.guild.id)
        except Exception as e:
            print(f"Error cleaning up guild data: {e}")

@bot.command(name='play_file')
async def play_file(ctx, *, file: discord.Attachment = None):
    if file is None:
        if len(ctx.message.attachments) > 0:
            file = ctx.message.attachments[0]
        else:
            await ctx.send("Please attach a file to play from.")
            return

    if file is None:
        await ctx.send("Please attach a file to play from.")
        return

    try:
        file_content = await file.read()
        urls = file_content.decode('utf-8').splitlines()
        
        if not urls:
            await ctx.send("The file is empty.")
            return

        await ctx.send(f"Adding {len(urls)} songs to the queue...")

        song_urls = []
        for url in urls:
            song_urls.extend(await music_url_getter.get_urls(url))
        
        await db_utils.add_to_queue(ctx.guild.id, song_urls)

        guild = await db_utils.get_guild(ctx.guild.id)
        if not guild:
            await db_utils.create_new_guild(ctx.guild.id)
            try:
                if not ctx.author.voice or not ctx.author.voice.channel:
                    error_msg = "❗ You must be in a voice channel to use this command!"
                    if ctx.message:
                        await ctx.send(error_msg)
                    else:
                        await ctx.respond(error_msg)
                    return
                
                await ctx.author.voice.channel.connect()
                print(f"Successfully connected to voice channel: {ctx.author.voice.channel.name}")
                
            except discord.errors.ClientException as e:
                error_msg = "❗ Failed to connect to voice channel. The bot might already be connected elsewhere."
                print(f"Voice connection error: {e}")
                if ctx.message:
                    await ctx.send(error_msg)
                else:
                    await ctx.respond(error_msg)
                return
                
            except Exception as e:
                error_msg = "❗ An error occurred while connecting to the voice channel. Please try again."
                print(f"Unexpected voice connection error: {e}")
                if ctx.message:
                    await ctx.send(error_msg)
                else:
                    await ctx.respond(error_msg)
                return
        
        try:
            while True:
                url = await db_utils.get_queue_entry(ctx.guild.id)

                if not url:
                    break

                try:
                    await player.play(ctx, url)
                except Exception as e:
                    print(f"Error playing song {url}: {e}")
                    try:
                        error_embed = await embed_generator.create_embed("Error", f"Failed to play a song. Skipping to next...")
                        if ctx.message:
                            await ctx.send(embed=error_embed)
                        else:
                            await ctx.respond(embed=error_embed)
                    except:
                        pass
                    continue
                    
        except Exception as e:
            print(f"Critical error in play loop: {e}")
        finally:
            voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            
            if voice_client:
                try:
                    await voice_client.disconnect()
                except:
                    pass
                
            try:
                await db_utils.delete_guild(ctx.guild.id)
            except Exception as e:
                print(f"Error cleaning up guild data: {e}")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name="information", aliases=['v', 'ver', 'version'])
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
        print(f"Error in version command: {e}")
        # Fallback to simple version display
        if ctx.message:
            await ctx.send(f"PianoNics-Music v{get_version()}")
        else:
            await ctx.respond(f"PianoNics-Music v{get_version()}")

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

@bot.slash_command(name="play", description="Plays the provided audio", options=[Option(name="query", required=True)])
async def play_slash(ctx, query: str):
    await play_command(ctx, query=query)

@bot.slash_command(name="play_file", description="Plays songs from a file", options=[Option(name="file", description="The file to play songs from", type=discord.Attachment, required=True)])
async def play_file_slash(ctx, file: discord.Attachment):
    await play_file(ctx, file=file)

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
        voice_client: discord.VoiceClient | None = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        guild = await db_utils.get_guild(ctx.guild.id)
        
        status_embed = discord.Embed(
            title="🎵 Bot Status",
            color=0x282841
        )
        
        # Voice connection status
        if voice_client and voice_client.is_connected():
            channel_name = voice_client.channel.name if voice_client.channel else "Unknown"
            status_embed.add_field(
                name="🔊 Voice Status", 
                value=f"Connected to: `{channel_name}`", 
                inline=True
            )
            
            # Playing status
            if voice_client.is_playing():
                status_embed.add_field(name="▶️ Playback", value="Playing", inline=True)
            elif voice_client.is_paused():
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
            )
            
            # Loop and shuffle status
            loop_status = "🔄 On" if guild.loop_queue else "⏹️ Off"
            shuffle_status = "🔀 On" if guild.shuffle_queue else "➡️ Off"
            
            status_embed.add_field(name="Loop", value=loop_status, inline=True)
            status_embed.add_field(name="Shuffle", value=shuffle_status, inline=True)
        else:
            status_embed.add_field(name="📝 Queue", value="No active session", inline=True)
            status_embed.add_field(name="Loop", value="⏹️ Off", inline=True)
            status_embed.add_field(name="Shuffle", value="➡️ Off", inline=True)
          # Server info
        latency = round(bot.latency * 1000)
        status_embed.add_field(name="📡 Latency", value=f"{latency}ms", inline=True)
        
        status_embed.set_footer(text=get_full_version_info())
        
        if ctx.message:
            await ctx.send(embed=status_embed)
        else:
            await ctx.respond(embed=status_embed)
            
    except Exception as e:
        print(f"Error in status command: {e}")
        try:
            if ctx.message:
                await ctx.send("❗ An error occurred while getting status")
            else:
                await ctx.respond("❗ An error occurred while getting status")
        except:
            pass

bot.run(os.getenv('DISCORD_TOKEN'))
