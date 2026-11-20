<p align="center">
  <img src="image/Logo.png" width="180" alt="PianoNic's Music Bot Logo" />
</p>
<p align="center">
  <strong>PianoNic's Music Bot</strong><br/>
  Paste a link. It plays. Nothing to register.
</p>
<p align="center">
  <a href="https://github.com/PianoNic/PianoNicsMusic"><img src="https://badgetrack.pianonic.ch/badge?tag=piano-nics-music&label=visits&color=2c234a&style=flat" alt="visits" /></a>
  <a href="https://github.com/PianoNic/PianoNicsMusic/releases"><img src="https://img.shields.io/github/v/release/PianoNic/PianoNicsMusic?include_prereleases&color=2c234a&label=Latest%20Release" alt="Latest release" /></a>
  <a href="https://github.com/yt-dlp/yt-dlp"><img src="https://img.shields.io/badge/Powered%20by-yt--dlp-2c234a.svg" alt="yt-dlp" /></a>
  <img src="https://img.shields.io/badge/Python-3.13-2c234a.svg" alt="Python 3.13" />
</p>

---

## What is PianoNic's Music Bot?

A Discord music bot that plays whatever you paste at it - a YouTube link, a Spotify album, a SoundCloud set, a TikTok, a file you dragged into the channel, or just the name of a song.

Everything resolves inside the bot through [yt-dlp](https://github.com/yt-dlp/yt-dlp). One container, no sidecar. The bot upgrades yt-dlp on boot and every twelve hours, and since each lookup runs yt-dlp fresh, an upgrade applies to the next track without a restart. When a source changes something, the bot catches up on its own.

No API keys. Spotify included.

## Features

- **Anything with a link**: YouTube, Spotify, SoundCloud, TikTok, Instagram, direct audio files, Discord attachments, and everything else yt-dlp reaches.
- **Search without a link**: type a song name and the first sensible result plays.
- **Real playlists**: a YouTube playlist or radio mix, Spotify album or playlist, or SoundCloud set resolves in one call.
- **Spotify without credentials**: metadata comes off Spotify's public embed page and the audio from the top YouTube Music song match, so a Spotify link shows Spotify's title and cover art. Playlists past 100 tracks are read through the web player's anonymous token; if Spotify changes that, the bot falls back to the first 100.
- **Now Playing panel**: one message per session, edited in place, with a live progress bar, what plays next, and buttons for pause, skip, loop, shuffle and stop. Only people in the bot's voice channel can press them.
- **No gap between songs**: the next track is looked up a minute before the current one ends.
- **Queue control**: skip, loop, shuffle, force-play a track next, and see what is coming.
- **Sound shaping**: per-server volume and bass, adjusted live on the playing track. Earrape, if that is your thing.
- **Slash and prefix**: every command works as `/play` or as `.play`, `!play`, `$play`.
- **Stays up**: a source that is region-locked, private or DRM-protected is reported and skipped rather than killing the queue. Five failures in a row stop playback instead of burning through it.

## Get started

**1. Create `compose.yml`:**

```yaml
services:
  pianonic-music-bot:
    image: pianonic/pianonicsmusic:latest
    container_name: pianonic-music-bot
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
    restart: unless-stopped
```

**2. Create `.env` next to it:**

```env
DISCORD_TOKEN=your-token-here
```

**3. Start it:**

```bash
docker compose up -d
```

<details>
<summary><strong>Creating the Discord bot</strong></summary>

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Under **Bot**, click **Reset Token** and copy it. That is your `DISCORD_TOKEN`.
3. Under **OAuth2 → URL Generator**, tick the `bot` and `applications.commands` scopes.
4. Under Bot Permissions, tick **Connect** and **Speak**.
5. Open the generated URL and invite the bot to your server.

</details>

<details>
<summary><strong>Running without Docker</strong></summary>

```bash
git clone https://github.com/PianoNic/PianoNicsMusic.git
cd PianoNicsMusic
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Needs FFmpeg on `PATH` and a `DISCORD_TOKEN`.

Tests:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

</details>

## Commands

Every command works as a slash command and behind the `.`, `!` and `$` prefixes.

| Command | Aliases | What it does |
| :--- | :--- | :--- |
| `play` | `p`, `pl`, `add`, `enqueue` | Play a link, a search, or an attached file |
| `force_play` | `fp`, `forceplay` | Put a track next in line |
| `pause` / `resume` | `hold` / `continue` | Pause and resume |
| `skip` | `next`, `play_next` | Skip the current track |
| `stop` / `leave` | `disconnect`, `bye` | Stop, clear the queue and disconnect |
| `loop` | `lp`, `repeat` | Loop the queue |
| `shuffle` | | Randomise the queue order |
| `queue` | `q`, `list` | Show what is playing and what is next |
| `bot_status` | `status`, `now_playing` | Connection, queue and filter state |
| `volume` | `v`, `vol` | Set or show volume (0-100) |
| `volume_up` / `volume_down` | `vol+` / `vol-` | Step volume by 10% |
| `bass_boost` | `bass`, `b` | Set or show bass (0-200, 100 is flat) |
| `earrape` | `ear`, `er` | Toggle the distortion filter |
| `help` | `h`, `cmds` | List every command |
| `ping` | | Round-trip latency |
| `information` | `ver`, `version` | Version and runtime info |

## Configuration

| Variable | Required | Description |
| :--- | :--- | :--- |
| `DISCORD_TOKEN` | yes | Your bot token |
| `YTDLP_COOKIES` | no | Path to a Netscape cookies file, for when YouTube asks a server IP to sign in |
| `MAX_QUEUE_TRACKS` | no | Cap on one playlist. Defaults to `500` - some editorial playlists run to five figures |

## Troubleshooting

- **Nothing plays, everything errors.** A source changed and yt-dlp has not caught up yet. Check `docker compose logs`; restarting pulls the newest yt-dlp.
- **"The source wants a login."** YouTube flagged the server IP. Export cookies from a signed-in browser and point `YTDLP_COOKIES` at the file.
- **Links to your own network are refused.** On purpose: the bot will not fetch `localhost` or private addresses.
- **A single song fails.** Region locks, private videos and DRM-protected SoundCloud tracks are reported and skipped. Nothing to fix.
- **Bot joins but is silent.** FFmpeg is missing from the bot image, or it lacks Connect and Speak in that channel.

## License

[CC BY-NC 4.0](LICENSE.md). Copyright PianoNic.

Read it, change it, and run it for any noncommercial purpose. Commercial use is not licensed.

---

<p align="center">Made with care by <a href="https://github.com/PianoNic">PianoNic</a></p>
