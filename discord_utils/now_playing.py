"""One "Now Playing" message per session, edited in place, with playback buttons."""
import logging
import time
from dataclasses import dataclass

import discord

from db_utils import db_utils
from discord_utils import responses
from models.music_information import MusicInformation
from utils import get_footer_text

logger = logging.getLogger('PianoNicsMusic')

COLOR = 0x282841
BAR_CELLS = 14
# One edit per guild every 10 s stays far below Discord's 5-edits-per-5-s channel limit.
REFRESH_SECONDS = 10
# Button presses closer than this are ignored, so mashing can't hit the edit rate limit.
PRESS_COOLDOWN_SECONDS = 1.5


def clock(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def progress(elapsed: float, duration: float | None) -> str:
    if not duration:
        return f"🔴 **LIVE** `{clock(elapsed)}`"

    filled = min(BAR_CELLS - 1, int(elapsed / duration * BAR_CELLS))
    bar = "▬" * filled + "🔘" + "▬" * (BAR_CELLS - 1 - filled)
    return f"{bar} `{clock(min(elapsed, duration))} / {clock(duration)}`"


@dataclass
class Panel:
    message: discord.PartialMessage
    view: "Controls"
    track: MusicInformation | None = None
    source: object | None = None
    edited_at: float = 0.0


_panels: dict[int, Panel] = {}


async def render(guild_id: int, panel: Panel) -> discord.Embed:
    track = panel.track
    voice_client = panel.message.channel.guild.voice_client
    paused = bool(voice_client and voice_client.is_paused())
    guild = await db_utils.get_guild(guild_id)
    upcoming = await db_utils.peek_queue_entry(guild_id)
    remaining = await db_utils.count_remaining(guild_id)
    elapsed = panel.source.elapsed if panel.source else 0
    volume = panel.source.volume if panel.source else await db_utils.get_volume(guild_id)
    loop_on = bool(guild and guild.loop_queue)
    shuffle_on = bool(guild and guild.shuffle_queue)

    embed = discord.Embed(title=track.song_name[:256], url=track.webpage_url, color=COLOR)
    embed.set_author(name="⏸️ Paused" if paused else "🎶 Now Playing")
    embed.description = f"by **{track.author}**\n\n{progress(elapsed, track.duration)}"
    embed.set_thumbnail(url=track.image_url)

    if shuffle_on:
        next_up = "🔀 Shuffled"
    elif upcoming:
        next_up = (upcoming.title or "Unknown")[:100]
    else:
        next_up = "🔄 Queue restarts" if loop_on else "Nothing"

    embed.add_field(name="Up next", value=next_up, inline=True)
    embed.add_field(name="In queue", value=str(remaining), inline=True)
    embed.set_footer(
        text=f"🔊 {int(volume * 100)}%  ·  🔁 Loop {'on' if loop_on else 'off'}  ·  "
        f"🔀 Shuffle {'on' if shuffle_on else 'off'}  ·  {get_footer_text()}"
    )

    panel.view.sync(paused, loop_on, shuffle_on)
    return embed


class Controls(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.pressed_at = 0.0

    def sync(self, paused: bool, loop_on: bool, shuffle_on: bool):
        self.get_item("np:pause").emoji = "▶️" if paused else "⏸️"
        self.get_item("np:loop").style = discord.ButtonStyle.success if loop_on else discord.ButtonStyle.secondary
        self.get_item("np:shuffle").style = discord.ButtonStyle.success if shuffle_on else discord.ButtonStyle.secondary

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Same rule as the leave command: only listeners steer the music.
        voice_client = interaction.guild.voice_client if interaction.guild else None
        listener = interaction.user.voice.channel if getattr(interaction.user, "voice", None) else None

        if not (voice_client and listener and listener.id == voice_client.channel.id):
            await interaction.response.send_message("Join my voice channel to use these buttons.", ephemeral=True)
            return False

        # ponytail: one cooldown per panel, shared by everyone - per user if that ever feels unfair.
        if time.monotonic() - self.pressed_at < PRESS_COOLDOWN_SECONDS:
            await interaction.response.send_message("Slow down a little.", ephemeral=True)
            return False

        self.pressed_at = time.monotonic()
        return True

    async def redraw(self, interaction: discord.Interaction):
        panel = _panels.get(self.guild_id)

        if not panel or not panel.track:
            await interaction.response.defer()
            return

        panel.edited_at = time.monotonic()
        await interaction.response.edit_message(embed=await render(self.guild_id, panel), view=self)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary, custom_id="np:pause")
    async def pause(self, button, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client.is_paused():
            voice_client.resume()
        else:
            voice_client.pause()

        await self.redraw(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="np:skip")
    async def skip(self, button, interaction: discord.Interaction):
        await interaction.response.defer()
        interaction.guild.voice_client.stop()

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="np:loop")
    async def loop(self, button, interaction: discord.Interaction):
        await db_utils.toggle_loop(self.guild_id)
        await self.redraw(interaction)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="np:shuffle")
    async def shuffle(self, button, interaction: discord.Interaction):
        await db_utils.shuffle_playlist(self.guild_id)
        await self.redraw(interaction)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="np:stop")
    async def stop_playback(self, button, interaction: discord.Interaction):
        await interaction.response.defer()
        # An empty queue ends the play loop, which disconnects and cleans up.
        await db_utils.delete_queue(self.guild_id)
        interaction.guild.voice_client.stop()


async def show_loading(ctx, text: str):
    """Put the panel into its loading state, posting it on the first track of a session."""
    embed = discord.Embed(description=f"⏳ {text}", color=COLOR)
    panel = _panels.get(ctx.guild.id)

    if panel:
        panel.track = panel.source = None

        try:
            await panel.message.edit(embed=embed, view=panel.view)
            return
        except discord.HTTPException as error:
            # Someone deleted it; post a fresh one below.
            logger.info(f"Now Playing message gone, posting a new one: {error}")
            panel.view.stop()

    sent = await responses.reply(ctx, embed)

    if isinstance(sent, discord.Interaction):
        sent = await sent.original_response()

    # Edit through the channel with the bot token: an interaction's own token dies after 15 minutes.
    message = ctx.channel.get_partial_message(sent.id)
    view = Controls(ctx.guild.id)
    await message.edit(view=view)
    _panels[ctx.guild.id] = Panel(message=message, view=view)


async def show_track(guild_id: int, track: MusicInformation, source):
    panel = _panels.get(guild_id)

    if not panel:
        return

    panel.track, panel.source = track, source
    await refresh(guild_id, force=True)


async def refresh(guild_id: int, force: bool = False):
    panel = _panels.get(guild_id)

    if not panel or not panel.track:
        return

    if not force and time.monotonic() - panel.edited_at < REFRESH_SECONDS:
        return

    panel.edited_at = time.monotonic()

    try:
        await panel.message.edit(embed=await render(guild_id, panel), view=panel.view)
    except discord.HTTPException as error:
        logger.warning(f"Could not update Now Playing in guild {guild_id}: {error}")


async def close(guild_id: int):
    panel = _panels.pop(guild_id, None)

    if not panel:
        return

    panel.view.stop()

    try:
        await panel.message.edit(
            embed=discord.Embed(description="👋 Queue finished. Thanks for listening!", color=COLOR), view=None
        )
    except discord.HTTPException as error:
        logger.info(f"Could not close Now Playing in guild {guild_id}: {error}")
