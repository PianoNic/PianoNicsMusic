import logging
import threading
from typing import Optional

logger = logging.getLogger('PianoNicsMusic')

_guild_earrape_enabled: dict[int, bool] = {}
_earrape_lock = threading.Lock()

def register_earrape(guild_id: int, enabled: bool = False):
    with _earrape_lock:
        _guild_earrape_enabled[guild_id] = enabled

def unregister_earrape(guild_id: int):
    with _earrape_lock:
        if guild_id in _guild_earrape_enabled:
            del _guild_earrape_enabled[guild_id]

def set_guild_earrape(guild_id: int, enabled: bool) -> bool:
    try:
        with _earrape_lock:
            _guild_earrape_enabled[guild_id] = enabled
        return True
    except Exception as e:
        logger.error(f"Error setting earrape for guild {guild_id}: {e}")
        return False

def toggle_guild_earrape(guild_id: int) -> Optional[bool]:
    try:
        with _earrape_lock:
            current_state = _guild_earrape_enabled.get(guild_id, False)
            new_state = not current_state
            _guild_earrape_enabled[guild_id] = new_state
            return new_state
    except Exception as e:
        logger.error(f"Error toggling earrape for guild {guild_id}: {e}")
        return None

def get_guild_earrape(guild_id: int) -> bool:
    with _earrape_lock:
        return _guild_earrape_enabled.get(guild_id, False)
