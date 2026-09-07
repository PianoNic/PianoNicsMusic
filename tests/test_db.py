import asyncio
import sys
import types
import unittest

from peewee import SqliteDatabase

from db_utils.db import db, setup_db


class TestDB(unittest.TestCase):
    def test_db_is_sqlite_memory(self):
        self.assertIsInstance(db, SqliteDatabase)
        self.assertEqual(str(db.database), ':memory:')

    def test_setup_db_runs(self):
        db.is_connection_usable = lambda: False
        db.connect = lambda: None
        db.create_tables = lambda tables, safe: None

        stubbed = {
            'models.guild_music_information': types.SimpleNamespace(Guild='Guild'),
            'models.queue_object': types.SimpleNamespace(QueueEntry='QueueEntry'),
        }
        original = {name: sys.modules.get(name) for name in stubbed}
        sys.modules.update(stubbed)

        try:
            asyncio.run(setup_db())
        finally:
            for name, module in original.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module


if __name__ == '__main__':
    unittest.main()
