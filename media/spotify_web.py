"""Anonymous Spotify web-player client for playlists past the embed page's 100 tracks.

Ported from ArgonFetch's SpotifyWebPlayerClient. Fragile by nature: it relies on a
third-party mirror of Spotify's rotating TOTP secret and on the web player's internal
token endpoint, persisted-query hash and response shape, any of which can change.
Every failure surfaces as RuntimeError so callers can fall back to the embed page.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import ssl
import struct
import sys
import time

import aiohttp
import certifi

SECRETS_URL = "https://code.thetadev.de/ThetaDev/spotify-secrets/raw/branch/main/secrets/secretDict.json"
SERVER_TIME_URL = "https://open.spotify.com/api/server-time"
TOKEN_URL = "https://open.spotify.com/api/token"
WEB_PLAYER_URL = "https://open.spotify.com/"
PATHFINDER_URL = "https://api-partner.spotify.com/pathfinder/v2/query"

# Anything not looking like desktop Chrome gets the mobile page, which has no readable bundle.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36")
PAGE_SIZE = 100
MAX_TRACKS = 10_000
MAX_BUNDLES = 5
TIMEOUT = aiohttp.ClientTimeout(total=20)
# No "br": aiohttp's brotli support depends on whichever brotli package is installed.
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
# certifi, not the OS store: Windows stores can lack the secret mirror's root CA.
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

BUNDLE_URL = re.compile(r"https://open\.spotifycdn\.com/cdn/build/web-player/[^\"'\s]+\.js")
PERSISTED_QUERY = re.compile(r'"(\w+)","query","([0-9a-f]{64})"')

_token: tuple[str, float] | None = None  # (token, expires_at unix seconds)
_hash: str | None = None


def _totp(secret: list[int], unix_seconds: int) -> str:
    key = "".join(str(v ^ ((i % 33) + 9)) for i, v in enumerate(secret)).encode()
    digest = hmac.new(key, struct.pack(">Q", unix_seconds // 30), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


async def _get_json(session: aiohttp.ClientSession, url: str, **kwargs):
    async with session.get(url, **kwargs) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def _server_time(session: aiohttp.ClientSession) -> int:
    # The code is only valid for 30 s, so prefer Spotify's clock over ours.
    try:
        return int((await _get_json(session, SERVER_TIME_URL))["serverTime"])
    except Exception:
        return int(time.time())


async def _access_token(session: aiohttp.ClientSession, refresh: bool = False) -> str:
    global _token
    if not refresh and _token and _token[1] > time.time():
        return _token[0]

    secrets = await _get_json(session, SECRETS_URL)
    version = max((int(k) for k in secrets if k.isdigit()), default=0)
    if not version:
        raise RuntimeError("secret mirror returned nothing usable")
    code = _totp(secrets[str(version)], await _server_time(session))

    params = {"reason": "init", "productType": "web-player",
              "totp": code, "totpServer": code, "totpVer": str(version)}
    data = await _get_json(session, TOKEN_URL, params=params)
    token = data.get("accessToken")
    if not token:
        raise RuntimeError("Spotify returned no access token")
    expires_ms = data.get("accessTokenExpirationTimestampMs")
    expires_at = expires_ms / 1000 if expires_ms else time.time() + 1800
    _token = (token, expires_at - 60)
    return token


async def _fetch_playlist_hash(session: aiohttp.ClientSession) -> str:
    global _hash
    if _hash:
        return _hash

    async with session.get(WEB_PLAYER_URL) as resp:
        resp.raise_for_status()
        home = await resp.text()
    scripts = sorted(dict.fromkeys(BUNDLE_URL.findall(home)), key=lambda u: "/web-player." not in u)
    if not scripts:
        raise RuntimeError("web player page listed no bundles")

    for script in scripts[:MAX_BUNDLES]:
        try:
            async with session.get(script) as resp:
                resp.raise_for_status()
                bundle = await resp.text()
        except aiohttp.ClientError:
            continue
        for name, sha in PERSISTED_QUERY.findall(bundle):
            if name == "fetchPlaylist":
                _hash = sha
                return sha
    raise RuntimeError("no fetchPlaylist query hash in web player bundles")


def _read_track(entry: dict) -> tuple[str, str] | None:
    data = (entry.get("itemV2") or {}).get("data") or {}
    if not str(data.get("uri", "")).startswith("spotify:track:") or not data.get("name"):
        return None  # local files, episodes, unavailable items
    artists = ((data.get("artists") or {}).get("items")) or []
    names = [(a.get("profile") or {}).get("name") for a in artists]
    return data["name"], ", ".join(n for n in names if n)


async def _fetch_page(session, playlist_id: str, offset: int, token: str, sha: str):
    """Returns (tracks, total, raw item count), or None when the token was rejected."""
    payload = {
        "variables": {"uri": f"spotify:playlist:{playlist_id}", "offset": offset,
                      "limit": PAGE_SIZE, "enableWatchFeedEntrypoint": False},
        "operationName": "fetchPlaylist",
        "extensions": {"persistedQuery": {"version": 1, "sha256Hash": sha}},
    }
    headers = {"authorization": f"Bearer {token}", "accept": "application/json"}
    async with session.post(PATHFINDER_URL, json=payload, headers=headers) as resp:
        if resp.status == 401:
            return None
        if resp.status != 200:
            raise RuntimeError(f"playlist API answered {resp.status}")
        body = await resp.json(content_type=None)

    if body.get("errors"):
        raise RuntimeError(f"playlist API error: {body['errors'][0].get('message')}")
    content = ((body.get("data") or {}).get("playlistV2") or {}).get("content")
    if content is None:
        raise RuntimeError("playlist not found or not public")
    items = content.get("items") or []
    return [t for t in map(_read_track, items) if t], int(content.get("totalCount") or 0), len(items)


async def playlist_tracks(playlist_id: str, limit: int) -> tuple[list[tuple[str, str]], int]:
    """(title, artists) for a public playlist, in order, up to `limit`, plus the playlist's total. Raises RuntimeError."""
    limit = min(limit, MAX_TRACKS)
    tracks: list[tuple[str, str]] = []
    try:
        connector = aiohttp.TCPConnector(ssl=SSL_CONTEXT)
        async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS, connector=connector) as session:
            token = await _access_token(session)
            sha = await _fetch_playlist_hash(session)
            offset, total, refreshed = 0, None, False
            while len(tracks) < limit and (total is None or offset < total):
                page = await _fetch_page(session, playlist_id, offset, token, sha)
                if page is None:
                    if refreshed:
                        raise RuntimeError("Spotify rejected a fresh token")
                    token, refreshed = await _access_token(session, refresh=True), True
                    continue
                found, total, raw_count = page
                if not raw_count:
                    break
                tracks.extend(found)
                offset += raw_count
    except (aiohttp.ClientError, asyncio.TimeoutError, AttributeError, KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Spotify web player request failed: {type(e).__name__}: {e}") from e
    return tracks[:limit], max(total or 0, len(tracks))


if __name__ == "__main__":
    async def _main(pid: str) -> None:
        start = time.perf_counter()
        result, total = await playlist_tracks(pid, MAX_TRACKS)
        print(f"{len(result)} of {total} tracks in {time.perf_counter() - start:.1f}s")
        for title, artists in result[:3]:
            print(f"  {title} - {artists}")

    asyncio.run(_main(sys.argv[1]))
