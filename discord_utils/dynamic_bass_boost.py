import logging
import threading
from typing import Optional

logger = logging.getLogger('PianoNicsMusic')

_guild_bass_boost_levels: dict[int, float] = {}
_bass_boost_lock = threading.Lock()

def register_bass_boost(guild_id: int, bass_level: float = 0.0):
    with _bass_boost_lock:
        _guild_bass_boost_levels[guild_id] = max(0.0, min(2.0, bass_level))

def unregister_bass_boost(guild_id: int):
    with _bass_boost_lock:
        if guild_id in _guild_bass_boost_levels:
            del _guild_bass_boost_levels[guild_id]

def get_bass_boost(guild_id: int) -> float:
    with _bass_boost_lock:
        return _guild_bass_boost_levels.get(guild_id, 0.0)

def set_guild_bass_boost(guild_id: int, bass_level: float) -> bool:
    try:
        bass_level = max(0.0, min(2.0, bass_level))
        with _bass_boost_lock:
            _guild_bass_boost_levels[guild_id] = bass_level
        return True
    except Exception as e:
        logger.error(f"Error setting bass boost for guild {guild_id}: {e}")
        return False

def adjust_guild_bass_boost(guild_id: int, adjustment: float) -> Optional[float]:
    try:
        with _bass_boost_lock:
            current_level = _guild_bass_boost_levels.get(guild_id, 0.0)
            new_level = max(0.0, min(2.0, current_level + adjustment))
            _guild_bass_boost_levels[guild_id] = new_level
            return new_level
    except Exception as e:
        logger.error(f"Error adjusting bass boost for guild {guild_id}: {e}")
        return None

def get_guild_current_bass_boost(guild_id: int) -> Optional[float]:
    with _bass_boost_lock:
        return _guild_bass_boost_levels.get(guild_id, 0.0)
