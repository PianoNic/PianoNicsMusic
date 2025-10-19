import asyncio
import discord
import logging

from discord_utils import embed_generator
from discord_utils.dynamic_volume import DynamicVolumeTransformer, register_audio_source, unregister_audio_source
from discord_utils.dynamic_bass_boost import register_bass_boost, unregister_bass_boost
from platform_handlers import music_url_getter
from ddl_retrievers.universal_ddl_retriever import YouTubeError
from db_utils import db_utils

logger = logging.getLogger('PianoNicsMusic')

async def play(ctx: discord.ApplicationContext, queue_url: str):
    loading_message = None
    try:
        try:
            loading_message = await ctx.respond(embed=await embed_generator.create_embed("Please Wait", "Searching song..."))
        except:
            loading_message = await ctx.send(embed=await embed_generator.create_embed("Please Wait", "Searching song..."))

        try:
            music_information = await music_url_getter.get_streaming_url(queue_url)
        except YouTubeError as e:
            # Handle YouTube-specific errors with user-friendly messages
            logger.error(f"YouTube error for {queue_url}: {e}")
            if loading_message:
                await loading_message.edit(embed=await embed_generator.create_embed("⚠️ Video Error", str(e)))
            raise YouTubeError(str(e))  # Keep as YouTubeError to preserve error type
        except Exception as e:
            logger.error(f"Error getting streaming URL for {queue_url}: {e}")
            if loading_message:
                await loading_message.edit(embed=await embed_generator.create_embed("Error", "Failed to get song information. Skipping..."))
            raise Exception(f"Failed to get streaming URL: {e}")

        try:
            await loading_message.edit(embed=await embed_generator.create_embed("Now Playing", f"**{music_information.song_name}**\nBy **{music_information.author}**", music_information.image_url))
        except Exception as e:
            logger.error(f"Error updating loading message: {e}")
        
        voice_client: discord.VoiceClient = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        
        if not voice_client:
            logger.error("No voice client found")
            raise Exception("Bot is not connected to a voice channel")
        
        # Add a small delay and check if voice client is actually connected
        await asyncio.sleep(0.1)
        if not voice_client.is_connected():
            logger.warning("Voice client exists but is not connected, retrying...")
            # Wait a bit more for connection to establish
            await asyncio.sleep(1)
            if not voice_client.is_connected():
                logger.error("Voice client still not connected after retry")
                raise Exception("Not connected to voice.")
            
        try:
            # Get the current volume and bass boost for this guild
            volume = await db_utils.get_volume(ctx.guild.id)
            bass_boost = await db_utils.get_bass_boost(ctx.guild.id)

            # Build FFmpeg filter chain with bass boost
            # bass_boost ranges from 0.0 to 2.0, converted to dB gain (-12dB to 12dB)
            bass_db = (bass_boost - 1.0) * 12  # Convert 0-2 range to -12 to 12 dB
            filter_audio = f'loudnorm=I=-25:TP=-1.5:LRA=11,equalizer=f=100:t=h:width_type=o:width=2:g={bass_db:.1f}'

            # Use FFmpeg audio normalization and bass boost filters
            audio_source = discord.FFmpegPCMAudio(
                music_information.streaming_url,
                options=f'-vn -filter:a "{filter_audio}"',
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            )

            # Apply dynamic volume transformation
            audio_source = DynamicVolumeTransformer(audio_source, volume=volume)

            # Register the audio source for real-time volume control and bass boost
            register_audio_source(ctx.guild.id, audio_source)
            register_bass_boost(ctx.guild.id, bass_boost)
            
            # Stop any currently playing audio before starting new playback
            if voice_client.is_playing():
                voice_client.stop()
                # Wait a moment for the stop to take effect
                await asyncio.sleep(0.5)

            voice_client.play(audio_source)
            
        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            raise Exception(f"Failed to start audio playback: {e}")
            
        # Wait for playback to finish with better error handling
        try:
            while voice_client.is_connected() and (voice_client.is_playing() or voice_client.is_paused()):
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error during playback monitoring: {e}")
            # Don't raise here, just log the error
        finally:
            # Unregister the audio source when playback finishes
            unregister_audio_source(ctx.guild.id)
            unregister_bass_boost(ctx.guild.id)
                
    except YouTubeError as e:
        # Don't overwrite the specific YouTube error message that was already set
        logger.error(f"Error in play function: {e}")
        raise e  # Re-raise the exception so the main loop can handle it
    except Exception as e:
        logger.error(f"Error in play function: {e}")
        if loading_message:
            try:
                await loading_message.edit(embed=await embed_generator.create_embed("Error", "An error occurred while playing this song."))
            except:
                pass  # Ignore message edit errors
        raise e  # Re-raise the exception so the main loop can handle it