from dataclasses import dataclass, field

@dataclass
class MusicInformation:
    streaming_url: str
    song_name: str
    author: str
    image_url: str
    # Some sources refuse a stream fetched without the headers it was resolved with.
    http_headers: dict = field(default_factory=dict)
    duration: float | None = None
    webpage_url: str | None = None
