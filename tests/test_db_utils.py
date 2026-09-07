import unittest
from unittest.mock import patch, MagicMock
import asyncio
from db_utils import db_utils
from models.dtos.QueueEntryDto import QueueEntryDto
from media.argonfetch import Track

class TestDBUtils(unittest.IsolatedAsyncioTestCase):
    @patch('db_utils.db_utils.Guild')
    async def test_create_new_guild_success(self, mock_guild):
        mock_guild.create.return_value = None
        await db_utils.create_new_guild(123)
        mock_guild.create.assert_called_once()

    @patch('db_utils.db_utils.Guild')
    async def test_create_new_guild_exists(self, mock_guild):
        mock_guild.create.side_effect = Exception('exists')
        mock_guild.get_or_none.return_value = True
        await db_utils.create_new_guild(123)
        mock_guild.get_or_none.assert_called_once()

    @patch('db_utils.db_utils.Guild')
    async def test_create_new_guild_error(self, mock_guild):
        mock_guild.create.side_effect = Exception('fail')
        mock_guild.get_or_none.return_value = None
        with self.assertRaises(Exception):
            await db_utils.create_new_guild(123)

    @patch('db_utils.db_utils.Guild')
    async def test_get_guild_found(self, mock_guild):
        mock_guild.get_or_none.return_value = MagicMock()
        with patch('db_utils.db_utils.guild_music_information_mapper.map', return_value='dto') as mock_map:
            result = await db_utils.get_guild(123)
            self.assertEqual(result, 'dto')
            mock_map.assert_called_once()

    @patch('db_utils.db_utils.Guild')
    async def test_get_guild_not_found(self, mock_guild):
        mock_guild.get_or_none.return_value = None
        result = await db_utils.get_guild(123)
        self.assertIsNone(result)

    @patch('db_utils.db_utils.QueueEntry')
    async def test_delete_queue(self, mock_queue):
        mock_query = MagicMock()
        mock_queue.delete.return_value.where.return_value.execute.return_value = None
        await db_utils.delete_queue(1)
        mock_queue.delete.assert_called_once()

    @patch('db_utils.db_utils.db')
    @patch('db_utils.db_utils.QueueEntry')
    async def test_add_to_queue_bulk(self, mock_queue, mock_db):
        tracks = [
            Track(url='url1', title='One', author='A', image_url=None),
            Track(url='url2', title='Two', author='B', image_url=None),
        ]
        await db_utils.add_to_queue(1, tracks)
        mock_queue.bulk_create.assert_called_once()

    @patch('db_utils.db_utils.db')
    @patch('db_utils.db_utils.QueueEntry')
    async def test_add_to_queue_empty(self, mock_queue, mock_db):
        await db_utils.add_to_queue(1, [])
        mock_queue.bulk_create.assert_not_called()

    @patch('db_utils.db_utils.QueueEntry')
    async def test_add_force_next_play_to_queue(self, mock_queue):
        track = Track(url='url', title='One', author='A', image_url=None)
        await db_utils.add_force_next_play_to_queue(1, track)
        mock_queue.create.assert_called_once_with(
            guild=1, url='url', title='One', author='A', image_url=None,
            already_played=False, force_play=True,
        )

    @patch('db_utils.db_utils.Guild')
    async def test_delete_guild(self, mock_guild):
        await db_utils.delete_guild(1)
        mock_guild.delete_by_id.assert_called_once_with(1)

    @patch('db_utils.db_utils.QueueEntry')
    async def test_get_queue(self, mock_queue):
        mock_entry = MagicMock(url='url', already_played=False, title='One', author='A')
        mock_queue.select.return_value.where.return_value = [mock_entry]
        result = await db_utils.get_queue(1)
        self.assertEqual(
            result, [QueueEntryDto(url='url', already_played=False, title='One', author='A')]
        )

if __name__ == '__main__':
    asyncio.run(unittest.main())
