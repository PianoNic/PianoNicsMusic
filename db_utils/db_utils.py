import random
import logging
from typing import List
from models.dtos.QueueEntryDto import QueueEntryDto
from models.dtos.GuildDto import GuildDto
from models.guild_music_information import Guild
from models.queue_object import QueueEntry
from models.mappers import guild_music_information_mapper
from db_utils.db import db
from media.argonfetch import Track

logger = logging.getLogger('PianoNicsMusic')

async def create_new_guild(discord_guild_id: int):
    try:
        Guild.create(id=discord_guild_id, loop_queue=False, shuffle_queue=False, volume=1.0, bass_boost=1.0)
    except Exception as e:
        logger.error(f"Error creating guild {discord_guild_id}: {e}")
        # Try to get existing guild if creation failed
        existing_guild = Guild.get_or_none(Guild.id == discord_guild_id)
        if not existing_guild:
            raise e

async def get_guild(discord_guild_id: int) -> GuildDto | None: 
    try:
        guild = Guild.get_or_none(Guild.id == discord_guild_id)
        if guild:
            return guild_music_information_mapper.map(guild)
        return None
    except Exception as e:
        logger.error(f"Error getting guild {discord_guild_id}: {e}")
        return None

async def delete_queue(guild_id: int):
    try:
        QueueEntry.delete().where(QueueEntry.guild == guild_id).execute()
    except Exception as e:
        logger.error(f"Error deleting queue for guild {guild_id}: {e}")
        # Continue anyway, this is cleanup

async def add_to_queue(guild_id: int, tracks: List[Track]):
    if not tracks:
        return

    entries = [
        QueueEntry(
            guild=guild_id,
            url=track.url,
            title=track.title,
            author=track.author,
            image_url=track.image_url,
            already_played=False,
            force_play=False,
        )
        for track in tracks
    ]

    # A playlist can be hundreds of rows and SQLite caps the variables per statement.
    with db.atomic():
        QueueEntry.bulk_create(entries, batch_size=100)

async def add_force_next_play_to_queue(guild_id: int, track: Track):
    QueueEntry.create(
        guild=guild_id,
        url=track.url,
        title=track.title,
        author=track.author,
        image_url=track.image_url,
        already_played=False,
        force_play=True,
    )

async def delete_guild(discord_guild_id: int):
    Guild.delete_by_id(discord_guild_id)

async def get_queue(guild_id: int) -> List[QueueEntryDto]:
    queue_entries = QueueEntry.select().where(QueueEntry.guild == guild_id)
    return [
        QueueEntryDto(
            url=entry.url,
            title=entry.title,
            author=entry.author,
            already_played=entry.already_played,
        )
        for entry in queue_entries
    ]

async def _get_random_queue_entry(guild_id: int) -> QueueEntry | None:
    queue_entries = QueueEntry.select().where((QueueEntry.guild == guild_id) & (QueueEntry.already_played == False))
    if not queue_entries:
        return None
    return random.choice(list(queue_entries))

async def _mark_entry_as_listened(entry: QueueEntry):
    try:
        entry.already_played = True
        entry.force_play = False
        entry.save()
    except Exception as e:
        logger.error(f"Error marking entry as listened: {e}")

async def _next_entry(guild: Guild, guild_id: int) -> QueueEntry | None:
    force_play_entry = QueueEntry.get_or_none(
        (QueueEntry.guild == guild_id) &
        (QueueEntry.already_played == False) &
        (QueueEntry.force_play == True)
    )

    if force_play_entry:
        return force_play_entry

    if guild.shuffle_queue:
        return await _get_random_queue_entry(guild_id)

    return QueueEntry.select().where(
        (QueueEntry.guild == guild_id) &
        (QueueEntry.already_played == False)
    ).order_by(QueueEntry.id).first()


async def get_queue_entry(guild_id: int) -> str | None:
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return None
        
        entry = await _next_entry(guild, guild_id)

        if entry:
            await _mark_entry_as_listened(entry)
            return entry.url
        
        if guild.loop_queue:
            try:
                QueueEntry.update(already_played=False).where(QueueEntry.guild == guild_id).execute()
                return await _get_entry_after_reset(guild_id)
            except Exception as e:
                logger.error(f"Error resetting queue for guild {guild_id}: {e}")
                return None
        
        # If we reach here, the queue is finished and not looping - clear it
        try:
            await delete_queue(guild_id)
            logger.info(f"Queue cleared for guild {guild_id} - all songs played")
        except Exception as e:
            logger.error(f"Error clearing finished queue for guild {guild_id}: {e}")
        
        return None
    except Exception as e:
        logger.error(f"Error getting queue entry for guild {guild_id}: {e}")
        return None

async def _get_entry_after_reset(guild_id: int) -> str | None:
    guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
    if not guild:
        return None

    entry = await _next_entry(guild, guild_id)

    if entry:
        await _mark_entry_as_listened(entry)
        return entry.url
    
    return None

async def shuffle_playlist(guild_id: int) -> bool:
    guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
    if not guild:
        return False
    
    guild.shuffle_queue = not guild.shuffle_queue
    guild.save()
    
    return guild.shuffle_queue

async def toggle_loop(guild_id: int) -> bool:
    guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
    if not guild:
        return False
    
    guild.loop_queue = not guild.loop_queue
    guild.save()
    
    return guild.loop_queue

async def is_queue_empty(guild_id: int) -> bool:
    """Check if the queue has any remaining unplayed songs"""
    try:
        remaining_entries = QueueEntry.select().where(
            (QueueEntry.guild == guild_id) & 
            (QueueEntry.already_played == False)
        ).count()
        return remaining_entries == 0
    except Exception as e:
        logger.error(f"Error checking if queue is empty for guild {guild_id}: {e}")
        return True

async def get_queue_total_entries(guild_id: int) -> int:
    """Get the total number of entries in the queue for a guild."""
    try:
        total_entries = QueueEntry.select().where(QueueEntry.guild == guild_id).count()
        return total_entries
    except Exception as e:
        logger.error(f"Error getting queue total entries for guild {guild_id}: {e}")
        return 0

async def clear_finished_queue_if_needed(guild_id: int):
    """Clear the queue if all songs have been played and loop is disabled"""
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return
        
        # Only clear if not looping and queue is empty
        if not guild.loop_queue and await is_queue_empty(guild_id):
            await delete_queue(guild_id)
            logger.info(f"Queue automatically cleared for guild {guild_id}")
    except Exception as e:
        logger.error(f"Error auto-clearing queue for guild {guild_id}: {e}")

async def set_volume(guild_id: int, volume: float) -> bool:
    """Set the volume for a guild. Volume should be between 0.0 and 1.0"""
    try:
        # Clamp volume between 0.0 and 1.0
        volume = max(0.0, min(1.0, volume))
        
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return False
        
        guild.volume = volume
        guild.save()
        return True
    except Exception as e:
        logger.error(f"Error setting volume for guild {guild_id}: {e}")
        return False

async def get_volume(guild_id: int) -> float:
    """Get the current volume for a guild"""
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return 1.0  # Default volume
        return guild.volume
    except Exception as e:
        logger.error(f"Error getting volume for guild {guild_id}: {e}")
        return 1.0  # Default volume

async def adjust_volume(guild_id: int, adjustment: float) -> float:
    """Adjust the volume by a certain amount. Returns the new volume level."""
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return 1.0

        new_volume = max(0.0, min(1.0, guild.volume + adjustment))
        guild.volume = new_volume
        guild.save()
        return new_volume
    except Exception as e:
        logger.error(f"Error adjusting volume for guild {guild_id}: {e}")
        return 1.0

async def set_bass_boost(guild_id: int, bass_level: float) -> bool:
    try:
        bass_level = max(0.0, min(2.0, bass_level))

        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return False

        guild.bass_boost = bass_level
        guild.save()
        return True
    except Exception as e:
        logger.error(f"Error setting bass boost for guild {guild_id}: {e}")
        return False

async def get_bass_boost(guild_id: int) -> float:
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return 1.0
        return guild.bass_boost
    except Exception as e:
        logger.error(f"Error getting bass boost for guild {guild_id}: {e}")
        return 1.0

async def adjust_bass_boost(guild_id: int, adjustment: float) -> float:
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return 1.0

        new_bass_boost = max(0.0, min(2.0, guild.bass_boost + adjustment))
        guild.bass_boost = new_bass_boost
        guild.save()
        return new_bass_boost
    except Exception as e:
        logger.error(f"Error adjusting bass boost for guild {guild_id}: {e}")
        return 1.0

async def set_earrape(guild_id: int, enabled: bool) -> bool:
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return False

        guild.earrape = enabled
        guild.save()
        return True
    except Exception as e:
        logger.error(f"Error setting earrape for guild {guild_id}: {e}")
        return False

async def get_earrape(guild_id: int) -> bool:
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return False
        return guild.earrape
    except Exception as e:
        logger.error(f"Error getting earrape for guild {guild_id}: {e}")
        return False

async def toggle_earrape(guild_id: int) -> bool:
    try:
        guild: Guild | None = Guild.get_or_none(Guild.id == guild_id)
        if not guild:
            return False

        guild.earrape = not guild.earrape
        guild.save()
        return guild.earrape
    except Exception as e:
        logger.error(f"Error toggling earrape for guild {guild_id}: {e}")
        return False