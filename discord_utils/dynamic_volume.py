"""
Real-time volume control for Discord audio playback
"""
import discord
from typing import Optional
import logging
import threading

logger = logging.getLogger('PianoNicsMusic')

class DynamicVolumeTransformer(discord.PCMVolumeTransformer):
    """A volume transformer that allows real-time volume changes"""
    
    def __init__(self, source, volume: float = 1.0):
        self._lock = threading.Lock()
        self._volume = volume
        self.frames = 0
        super().__init__(source, volume=volume)

    def read(self) -> bytes:
        # Discord pulls one 20 ms frame per read and stops pulling while paused.
        self.frames += 1
        return super().read()

    @property
    def elapsed(self) -> float:
        return self.frames * 0.02

    @property
    def volume(self) -> float:
        """Get the current volume level"""
        with self._lock:
            return self._volume
    
    @volume.setter
    def volume(self, value: float):
        """Set the volume level (0.0 to 1.0)"""
        with self._lock:
            # Clamp volume between 0.0 and 1.0
            self._volume = max(0.0, min(1.0, value))
            # Update the underlying PCMVolumeTransformer volume
            super(DynamicVolumeTransformer, self.__class__).volume.fset(self, self._volume)
    
    def adjust_volume(self, adjustment: float) -> float:
        """Adjust volume by a certain amount and return the new volume"""
        with self._lock:
            new_volume = max(0.0, min(1.0, self._volume + adjustment))
            self.volume = new_volume
            return new_volume

# Global dictionary to store audio sources by guild ID
_guild_audio_sources: dict[int, DynamicVolumeTransformer] = {}

def register_audio_source(guild_id: int, source: DynamicVolumeTransformer):
    """Register an audio source for a guild"""
    _guild_audio_sources[guild_id] = source

def unregister_audio_source(guild_id: int):
    """Unregister an audio source for a guild"""
    if guild_id in _guild_audio_sources:
        del _guild_audio_sources[guild_id]

def get_audio_source(guild_id: int) -> Optional[DynamicVolumeTransformer]:
    """Get the current audio source for a guild"""
    return _guild_audio_sources.get(guild_id)

def set_guild_volume(guild_id: int, volume: float) -> bool:
    """Set the volume for a guild's current audio"""
    source = get_audio_source(guild_id)
    if source:
        source.volume = volume
        return True
    return False

def adjust_guild_volume(guild_id: int, adjustment: float) -> Optional[float]:
    """Adjust the volume for a guild's current audio"""
    source = get_audio_source(guild_id)
    if source:
        return source.adjust_volume(adjustment)
    return None

def get_guild_current_volume(guild_id: int) -> Optional[float]:
    """Get the current volume for a guild's audio"""
    source = get_audio_source(guild_id)
    if source:
        return source.volume
    return None
