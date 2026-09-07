from dataclasses import dataclass

@dataclass
class QueueEntryDto:
    url: str
    already_played: bool
    title: str | None = None
    author: str | None = None
