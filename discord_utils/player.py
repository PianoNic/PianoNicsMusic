import asyncio
import logging
import shlex

import discord

from db_utils import db_utils
from discord_utils import now_playing
from discord_utils.dynamic_bass_boost import register_bass_boost, unregister_bass_boost
from discord_utils.dynamic_earrape import register_earrape, unregister_earrape
from discord_utils.dynamic_volume import DynamicVolumeTransformer, register_audio_source, unregister_audio_source
from media import resolver

logger = logging.getLogger('PianoNicsMusic')

CONNECTION_CHECK_SECONDS = 5
# Muse starts resolving the next song a minute before this one ends.
PREFETCH_LEAD_SECONDS = 60


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


async def wait_until_finished(voice_client, finished: asyncio.Event, on_tick=None):
    while not finished.is_set():
        if not voice_client.is_connected():
            return

        if on_tick:
            try:
                await on_tick()
            except Exception as error:
                logger.warning(f"Playback tick failed: {error}")

        try:
            await asyncio.wait_for(asyncio.shield(finished.wait()), timeout=CONNECTION_CHECK_SECONDS)
        except asyncio.TimeoutError:
            continue


async def play(ctx: discord.ApplicationContext, queue_url: str):
    await now_playing.show_loading(ctx, "Loading the next song...")

    # MediaError carries a message for the user; play_queue reports it and moves on.
    music_information = await resolver.get_playable(queue_url)

    voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)

    if not voice_client or not voice_client.is_connected():
        raise RuntimeError("Bot is not connected to a voice channel")

    volume = await db_utils.get_volume(ctx.guild.id)
    audio_filter = await build_filter(ctx.guild.id)

    # The whitelist keeps FFmpeg off file:// and friends, whatever URL reaches it.
    before_options = (
        "-nostdin -protocol_whitelist http,https,tcp,tls,crypto "
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    )

    if music_information.http_headers:
        headers = "".join(f"{key}: {value}\r\n" for key, value in music_information.http_headers.items())
        before_options += f" -headers {shlex.quote(headers)}"

    audio_source = discord.FFmpegPCMAudio(
        music_information.streaming_url,
        options=f'-vn -filter:a "{audio_filter}"',
        before_options=before_options,
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

    prefetched = False

    async def on_tick():
        nonlocal prefetched
        await now_playing.refresh(ctx.guild.id)

        remaining = (music_information.duration or 0) - audio_source.elapsed

        # A live stream has no end to count down to, so its successor is fetched right away.
        if not prefetched and remaining <= PREFETCH_LEAD_SECONDS:
            prefetched = True
            upcoming = await db_utils.peek_queue_entry(ctx.guild.id)

            if upcoming:
                resolver.prefetch(upcoming.url)

    try:
        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(audio_source, after=on_finished)
        await now_playing.show_track(ctx.guild.id, music_information, audio_source)

        await wait_until_finished(voice_client, finished, on_tick)
    finally:
        unregister_audio_source(ctx.guild.id)
        unregister_bass_boost(ctx.guild.id)
        unregister_earrape(ctx.guild.id)
