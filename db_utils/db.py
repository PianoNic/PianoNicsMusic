from peewee import SqliteDatabase
import logging

logger = logging.getLogger('PianoNicsMusic')

db = SqliteDatabase(':memory:')

async def setup_db():
    try:
        from models.guild_music_information import Guild
        from models.queue_object import QueueEntry

        # Connect to database
        if not db.is_connection_usable():
            db.connect()

        # Create tables if they don't exist
        db.create_tables([Guild, QueueEntry], safe=True)

        logger.info("In-memory database setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise e