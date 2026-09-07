import asyncio
import logging

import discord

from db_utils import db_utils
from discord_utils import embed_generator, responses
from discord_utils.dynamic_bass_boost import register_bass_boost, unregister_bass_boost
from discord_utils.dynamic_earrape import register_earrape, unregister_earrape
from discord_utils.dynamic_volume import DynamicVolumeTransformer, register_audio_source, unregister_audio_source
from media import resolver
from media.resolver import ArgonFetchError

logger = logging.getLogger('PianoNicsMusic')

CONNECTION_CHECK_SECONDS = 5


async def build_filter(guild_id: int) -> str:
    bass_boost = await db_utils.get_bass_boost(guild_id)
    earrape = await db_utils.get_earrape(guild_id)

    # 1.0 is neutral; the equalizer wants a gain either side of it.
    bass_db = (bass_boost - 1.0) * 12

    audio_filter = (
        f'loudnorm=I=-25:TP=-1.5:LRA=11,'
        f'equalizer=f=100:t=h:width_type=o:width=2:g={bass_db:.1f}'
    )

    if earrape:
        audio_filter += ',acrusher=level_in=8:level_out=8:bits=8:mode=log'

    return audio_filter


async def wait_until_finished(voice_client: discord.VoiceClient, finished: asyncio.Event):
    while not finished.is_set():
        if not voice_client.is_connected():
            return

        try:
            await asyncio.wait_for(asyncio.shield(finished.wait()), timeout=CONNECTION_CHECK_SECONDS)
        except asyncio.TimeoutError:
            continue


async def play(ctx: discord.ApplicationContext, queue_url: str):
    loading_message = await responses.reply(
        ctx, await embed_generator.create_embed("Please Wait", "Searching song...")
    )

    try:
        music_information = await resolver.get_playable(queue_url)
    except ArgonFetchError as error:
        logger.error(f"Could not resolve {queue_url}: {error}")
        await loading_message.edit(embed=await embed_generator.create_embed("⚠️ Track Error", str(error)))
        raise
    except Exception as error:
        logger.error(f"Error getting streaming URL for {queue_url}: {error}")
        await loading_message.edit(
            embed=await embed_generator.create_embed("Error", "Failed to get song information. Skipping...")
        )
        raise

    try:
        await loading_message.edit(
            embed=await embed_generator.create_embed(
                "Now Playing",
                f"**{music_information.song_name}**\nBy **{music_information.author}**",
                music_information.image_url,
            )
        )
    except Exception as error:
        logger.error(f"Error updating loading message: {error}")

    voice_client: discord.VoiceClient = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)

    if not voice_client or not voice_client.is_connected():
        raise RuntimeError("Bot is not connected to a voice channel")

    volume = await db_utils.get_volume(ctx.guild.id)
    audio_filter = await build_filter(ctx.guild.id)

    audio_source = discord.FFmpegPCMAudio(
        music_information.streaming_url,
        options=f'-vn -filter:a "{audio_filter}"',
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    )
    audio_source = DynamicVolumeTransformer(audio_source, volume=volume)

    register_audio_source(ctx.guild.id, audio_source)
    register_bass_boost(ctx.guild.id, await db_utils.get_bass_boost(ctx.guild.id))
    register_earrape(ctx.guild.id, await db_utils.get_earrape(ctx.guild.id))

    finished = asyncio.Event()
    loop = asyncio.get_running_loop()

    def on_finished(error):
        if error:
            logger.error(f"Playback error: {error}")

        loop.call_soon_threadsafe(finished.set)

    try:
        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(audio_source, after=on_finished)

        await wait_until_finished(voice_client, finished)
    finally:
        unregister_audio_source(ctx.guild.id)
        unregister_bass_boost(ctx.guild.id)
        unregister_earrape(ctx.guild.id)
