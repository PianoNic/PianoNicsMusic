from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

import aiohttp

from media import spotify_web
from models.music_information import MusicInformation

logger = logging.getLogger('PianoNicsMusic')

DEFAULT_MAX_TRACKS = 500
FALLBACK_COVER = "https://i.giphy.com/LNOZoHMI16ydtQ8bGG.webp"
RESOLVE_TIMEOUT_SECONDS = 90
SPOTIFY_EMBED_LIMIT = 100
UPDATE_INTERVAL_SECONDS = 12 * 60 * 60
# Stream URLs expire (YouTube's after ~6 h, others sooner); Muse re-resolves anything older than this.
PREFETCH_MAX_AGE_SECONDS = 10 * 60
SPOTIFY_LINK = re.compile(r"open\.spotify\.com/(?:[\w-]+/)?(track|album|playlist|artist)/([A-Za-z0-9]+)")
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


_prefetched: dict[str, tuple[float, asyncio.Task]] = {}


class MediaError(Exception):
    """Base error. Messages are written to be shown to the user."""


class NotFound(MediaError):
    pass


class Unsupported(MediaError):
    pass


class Unavailable(MediaError):
    pass


@dataclass(frozen=True)
class Track:
    url: str
    title: str
    author: str
    image_url: str | None


def max_tracks() -> int:
    try:
        return max(1, int(os.getenv("MAX_QUEUE_TRACKS", DEFAULT_MAX_TRACKS)))
    except ValueError:
        return DEFAULT_MAX_TRACKS


def is_url(query: str) -> bool:
    return urlparse(query).scheme in ("http", "https")


def normalize_query(query: str) -> str:
    """Point a watch?v=...&list=... link at its playlist, as this bot always has."""
    parsed = urlparse(query)
    hostname = parsed.hostname or ""

    if "youtube" not in hostname and "youtu" not in hostname:
        return query

    params = parse_qs(parsed.query)
    list_id = params.get("list", [None])[0]

    # A radio mix only lists from its watch link; /playlist?list=RD... is "unviewable".
    if not list_id or not params.get("v") or list_id.startswith("RD"):
        return query

    return urlunparse(parsed._replace(path="/playlist", query=urlencode({"list": list_id})))


async def ensure_public(url: str) -> None:
    """Refuse links into the host's own network; yt-dlp and FFmpeg would happily fetch them."""
    host = urlparse(url).hostname

    if not host:
        raise Unsupported("That link is not valid.")

    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(host, None)
    except OSError as error:
        raise NotFound("That website could not be found.") from error

    # ponytail: checks DNS once — a redirect to a private address still gets through; pin the IP if that matters.
    if any(not ipaddress.ip_address(address[4][0].split('%')[0]).is_global for address in addresses):
        raise Unsupported("That link points to a private network.")


def error_from(stderr: str) -> MediaError:
    text = stderr.lower()

    if "drm" in text:
        return Unsupported("This media is DRM protected and cannot be played.")
    if "unsupported url" in text:
        return Unsupported("That link is not supported.")
    if "confirm your age" in text or "age-restricted" in text:
        return Unsupported("This video is age restricted.")
    if any(hint in text for hint in ("sign in", "login required", "cookies", "rate-limit")):
        logger.error(f"yt-dlp wants a login: {stderr.strip()[-300:]}")
        return Unavailable("The source wants a login. The bot owner can set YTDLP_COOKIES.")
    if any(hint in text for hint in ("private", "unavailable", "not available", "does not exist", "unviewable", "404", "removed", "no video formats")):
        return NotFound("Nothing playable was found at that link.")

    logger.error(f"yt-dlp failed: {stderr.strip()[-500:]}")
    return Unavailable("Could not load that. Try again in a moment.")


async def ytdlp(*args: str) -> dict:
    # No JS runtime on purpose: with one, yt-dlp adds YouTube's TV client, whose
    # stream URLs answer 403 to server IPs. ArgonFetch learned this the hard way.
    options = ["-J", "--no-warnings", "--no-js-runtimes"]

    if os.getenv("YTDLP_COOKIES"):
        options += ["--cookies", os.environ["YTDLP_COOKIES"]]

    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "yt_dlp", *options, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), RESOLVE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as error:
        raise Unavailable("Loading that took too long.") from error
    finally:
        # Also covers a cancelled prefetch, so no yt-dlp is left running.
        if process.returncode is None:
            process.kill()

    if process.returncode:
        raise error_from(stderr.decode(errors="ignore"))

    return json.loads(stdout)


def cover_of(info: dict) -> str | None:
    thumbnails = info.get("thumbnails") or [{}]
    return info.get("thumbnail") or thumbnails[-1].get("url")


def author_of(info: dict) -> str:
    return info.get("artist") or info.get("uploader") or info.get("channel") or ""


def track_from(info: dict, fallback_url: str) -> Track:
    return Track(
        url=info.get("webpage_url") or info.get("url") or fallback_url,
        title=info.get("title") or "Unknown",
        author=author_of(info),
        image_url=cover_of(info),
    )


async def spotify_tracks(kind: str, spotify_id: str) -> tuple[list[Track], int]:
    """Tracks plus the playlist's total, which runs past the list when capped."""
    # Spotify streams are DRM'd, so each track is played as its top YouTube Music song match.
    # The embed page lists a track/album/playlist without an API key.
    url = f"https://open.spotify.com/embed/{kind}/{spotify_id}"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as response:
                html = await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        raise Unavailable("Spotify could not be reached.") from error

    match = NEXT_DATA.search(html)

    if not match:
        raise NotFound("Nothing was found at that Spotify link.")

    entity = json.loads(match.group(1))["props"]["pageProps"]["state"]["data"]["entity"]
    images = (entity.get("visualIdentity") or {}).get("image") or (entity.get("coverArt") or {}).get("sources") or [{}]
    cover = images[-1].get("url")

    items = entity.get("trackList") or [{
        "title": entity.get("name") or entity.get("title"),
        "subtitle": ", ".join(artist["name"] for artist in entity.get("artists") or []),
    }]

    listing = [(item.get("title") or "Unknown", (item.get("subtitle") or "").replace("\xa0", " ")) for item in items]

    total = len(listing)

    # The embed page stops at 100. Past that, ask the web player's own API (fragile, see spotify_web).
    if kind == "playlist" and len(listing) >= SPOTIFY_EMBED_LIMIT:
        try:
            web_listing, web_total = await spotify_web.playlist_tracks(spotify_id, max_tracks())

            if web_listing:
                listing, total = web_listing, web_total
        except RuntimeError as error:
            logger.warning(f"Spotify web player listing failed, keeping the first 100: {error}")

    tracks = [
        Track(
            url=f"https://music.youtube.com/search?q={quote(f'{artists} {title}')}#songs",
            title=title,
            author=artists,
            image_url=cover,
        )
        for title, artists in listing
    ]
    return tracks, total


async def get_tracks(query: str) -> tuple[list[Track], int]:
    """Expand a query into queue entries, plus how many the cap dropped."""
    limit = max_tracks()
    spotify = SPOTIFY_LINK.search(query)

    if spotify:
        tracks, total = await spotify_tracks(*spotify.groups())
    else:
        if is_url(query):
            await ensure_public(query)
            target = normalize_query(query)
        else:
            target = f"ytsearch1:{query}"

        # "--" stops a query like "--exec ..." from being read as an option.
        info = await ytdlp("--flat-playlist", "-I", f"1:{limit}", "--", target)
        entries = info.get("entries")

        if entries is None:
            tracks, total = [track_from(info, query)], 1
        else:
            tracks = [track_from(entry, query) for entry in entries if entry]
            total = max(info.get("playlist_count") or 0, len(tracks))

    if not tracks:
        raise NotFound("Nothing playable was found for that.")

    return tracks[:limit], max(0, total - limit)


def prefetch(url: str) -> None:
    """Start resolving a track before it is due, so the next song starts without the lookup wait."""
    now = time.monotonic()

    for key, (started, task) in list(_prefetched.items()):
        if now - started > PREFETCH_MAX_AGE_SECONDS:
            task.cancel()
            del _prefetched[key]

    if url not in _prefetched:
        task = asyncio.create_task(resolve_playable(url))
        # A failed prefetch is retried at play time; this only keeps asyncio from warning about it.
        task.add_done_callback(lambda done: done.cancelled() or done.exception())
        _prefetched[url] = (now, task)


async def get_playable(url: str) -> MusicInformation:
    started, task = _prefetched.pop(url, (0.0, None))

    if task and time.monotonic() - started <= PREFETCH_MAX_AGE_SECONDS:
        try:
            return await task
        except Exception as error:
            logger.info(f"Prefetch of {url} failed, resolving again: {error}")
    elif task:
        task.cancel()

    return await resolve_playable(url)


async def resolve_playable(url: str) -> MusicInformation:
    if is_url(url):
        await ensure_public(url)

    # -I 1: a search link (Spotify matches, typed text) plays its top hit.
    info = await ytdlp("--no-playlist", "-I", "1", "-f", "bestaudio/best", "--", url)

    # A search answers with a one-entry playlist.
    if "entries" in info:
        info = next(iter(info["entries"] or []), None)

    if not info or not info.get("url"):
        raise NotFound("This track is no longer available.")

    return MusicInformation(
        streaming_url=info["url"],
        song_name=info.get("title") or "Unknown",
        author=author_of(info) or "Unknown",
        image_url=cover_of(info) or FALLBACK_COVER,
        http_headers=info.get("http_headers") or {},
        duration=None if info.get("is_live") else info.get("duration"),
        webpage_url=info.get("webpage_url"),
    )


async def keep_ytdlp_updated():
    """Sources break yt-dlp every few weeks. yt-dlp runs as a subprocess, so an upgrade applies on the next track."""
    while True:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "yt-dlp[default]",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode:
            logger.warning(f"yt-dlp update failed: {stderr.decode(errors='ignore').strip()[-300:]}")
        else:
            logger.info("yt-dlp is up to date")

        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
