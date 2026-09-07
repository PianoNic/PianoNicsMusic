from models.guild_music_information import Guild
from models.queue_object import QueueEntry
from models.dtos.GuildDto import GuildDto
from models.mappers.queue_object_mapper import map as map_queue_entry

def map(guild: Guild) -> GuildDto:
    queue_entries = QueueEntry.select().where(QueueEntry.guild == guild)

    return GuildDto(
        discord_guild_id=guild.id,
        loop_queue=guild.loop_queue,
        shuffle_queue=guild.shuffle_queue,
        volume=guild.volume,
        bass_boost=guild.bass_boost,
        earrape=guild.earrape,
        queue=[map_queue_entry(entry) for entry in queue_entries]
    )
