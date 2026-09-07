from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger('PianoNicsMusic')

DEFAULT_BASE_URL = "http://argonfetch:8080"

TIMEOUT = aiohttp.ClientTimeout(total=180, connect=10)
MAINTENANCE_RETRIES = 3
MAINTENANCE_BACKOFF_SECONDS = 5


class ArgonFetchError(Exception):
    """Base error. Messages are written to be shown to the user."""


class NotFound(ArgonFetchError):
    pass


class Unsupported(ArgonFetchError):
    pass


class Unavailable(ArgonFetchError):
    pass


@dataclass(frozen=True)
class Track:
    url: str
    title: str
    author: str
    image_url: str | None


def base_url() -> str:
    return os.getenv("ARGONFETCH_URL", DEFAULT_BASE_URL).rstrip("/")


async def resolve(query: str) -> dict:
    url = f"{base_url()}/api/Fetch/GetResource?{urlencode({'url': query})}"

    for attempt in range(MAINTENANCE_RETRIES):
        try:
            async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()

                    # 503 means it is installing a yt-dlp update, which takes seconds.
                    if response.status == 503:
                        if attempt + 1 < MAINTENANCE_RETRIES:
                            await asyncio.sleep(MAINTENANCE_BACKOFF_SECONDS)
                            continue

                        raise Unavailable("The media service is updating itself. Try again in a moment.")

                    await _raise_for_status(response, query)

        except aiohttp.ClientError as error:
            logger.error(f"Could not reach ArgonFetch at {base_url()}: {error}")
            raise Unavailable("The media service is unreachable.") from error

        except asyncio.TimeoutError as error:
            logger.error(f"ArgonFetch timed out resolving {query}")
            raise Unavailable("The media service took too long to answer.") from error

    raise Unavailable("The media service is updating itself. Try again in a moment.")


async def _raise_for_status(response: aiohttp.ClientResponse, query: str) -> None:
    detail = ""

    try:
        problem = await response.json()
        detail = problem.get("detail") or problem.get("title") or ""
    except Exception:
        pass

    if response.status == 404:
        raise NotFound("Nothing was found at that link.")

    if response.status == 415:
        raise Unsupported(detail or "This media cannot be played.")

    logger.error(f"ArgonFetch answered {response.status} for {query}: {detail}")
    raise Unavailable("The media service could not handle that link.")


def best_audio_url(item: dict) -> str | None:
    renditions = ((item.get("audio") or {}).get("renditions")) or []

    # A rendition with convertTo is transcoded per request and advertises a higher
    # bitrate than the source it re-encodes, so it wins a naive bitrate comparison.
    sources = [r for r in renditions if not r.get("convertTo") and r.get("key")]

    if not sources:
        return None

    best = max(sources, key=lambda r: r.get("bitrate") or 0)

    return f"{base_url()}/api/Stream/Media/{best['key']}"


def track_from(item: dict, fallback_url: str) -> Track:
    return Track(
        url=item.get("requestedUrl") or fallback_url,
        title=item.get("title") or "Unknown",
        author=item.get("author") or "",
        image_url=item.get("coverUrl") or None,
    )
