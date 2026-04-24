from dataclasses import dataclass
from typing import Optional
from datetime import datetime


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
    play_count: int = 0
    likes_count: int = 0
    created_at: Optional[str] = None
    genre: Optional[str] = None

    @property
    def duration_str(self) -> str:
        total_sec = self.duration_ms // 1000
        mins, secs = divmod(total_sec, 60)
        return f"{mins}:{secs:02d}"

    @property
    def display_title(self) -> str:
        return f"{self.artist} — {self.title}"
    
    @property
    def play_count_str(self) -> str:
        """Format play count with human-readable suffix."""
        if self.play_count >= 1_000_000:
            return f"{self.play_count / 1_000_000:.1f}M"
        elif self.play_count >= 1_000:
            return f"{self.play_count / 1_000:.1f}K"
        return str(self.play_count)
    
    @property
    def likes_count_str(self) -> str:
        """Format likes count with human-readable suffix."""
        if self.likes_count >= 1_000_000:
            return f"{self.likes_count / 1_000_000:.1f}M"
        elif self.likes_count >= 1_000:
            return f"{self.likes_count / 1_000:.1f}K"
        return str(self.likes_count)
    
    @property
    def created_date_str(self) -> str:
        """Format created date as 'Mon DD' or empty if not available."""
        if not self.created_at:
            return ""
        try:
            dt = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            return dt.strftime("%b %d")
        except Exception:
            return ""
