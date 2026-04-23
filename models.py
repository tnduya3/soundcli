from dataclasses import dataclass
from typing import Optional


@dataclass
class Track:
    id: str
    title: str
    artist: str
    duration_ms: int
    stream_url: Optional[str] = None
    permalink_url: Optional[str] = None
    artwork_url: Optional[str] = None
    liked: bool = False

    @property
    def duration_str(self) -> str:
        total_sec = self.duration_ms // 1000
        mins, secs = divmod(total_sec, 60)
        return f"{mins}:{secs:02d}"

    @property
    def display_title(self) -> str:
        return f"{self.artist} — {self.title}"
