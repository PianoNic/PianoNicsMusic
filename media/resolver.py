from __future__ import annotations

import logging
import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from media import argonfetch
from media.argonfetch import ArgonFetchError, NotFound, Track, Unavailable, Unsupported
from models.music_information import MusicInformation

logger = logging.getLogger('PianoNicsMusic')

DEFAULT_MAX_TRACKS = 500
FALLBACK_COVER = "https://i.giphy.com/LNOZoHMI16ydtQ8bGG.webp"

__all__ = [
    "ArgonFetchError",
    "NotFound",
    "Unavailable",
    "Unsupported",
    "Track",
    "get_playable",
    "get_tracks",
    "normalize_query",
]


def max_tracks() -> int:
    try:
        return max(1, int(os.getenv("MAX_QUEUE_TRACKS", DEFAULT_MAX_TRACKS)))
    except ValueError:
        return DEFAULT_MAX_TRACKS


def normalize_query(query: str) -> str:
    """Point a watch?v=...&list=... link at its playlist, as this bot always has."""
    parsed = urlparse(query)
    hostname = parsed.hostname or ""

    if "youtube" not in hostname and "youtu" not in hostname:
        return query

    params = parse_qs(parsed.query)
    list_id = params.get("list", [None])[0]

    # ArgonFetch cannot list a radio mix yet (ArgonFetch/ArgonFetch#247), and playing
    # the seed track beats erroring.
    if not list_id or not params.get("v") or list_id.startswith("RD"):
        return query

    return urlunparse(parsed._replace(path="/playlist", query=urlencode({"list": list_id})))


async def get_tracks(query: str) -> tuple[list[Track], int]:
    """Expand a query into queue entries, plus how many the cap dropped."""
    data = await argonfetch.resolve(normalize_query(query))
    items = data.get("mediaItems") or []

    if not items:
        raise NotFound("Nothing playable was found for that.")

    tracks = [argonfetch.track_from(item, query) for item in items]
    limit = max_tracks()

    if len(tracks) > limit:
        return tracks[:limit], len(tracks) - limit

    return tracks, 0


async def get_playable(url: str) -> MusicInformation:
    data = await argonfetch.resolve(url)
    items = data.get("mediaItems") or []

    if not items:
        raise NotFound("This track is no longer available.")

    item = items[0]
    track = argonfetch.track_from(item, url)

    # A plain audio file resolves with no renditions; it is already the stream.
    stream_url = argonfetch.best_audio_url(item) or url

    return MusicInformation(
        streaming_url=stream_url,
        song_name=track.title,
        author=track.author or "Unknown",
        image_url=track.image_url or FALLBACK_COVER,
    )
