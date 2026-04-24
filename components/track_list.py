from __future__ import annotations
from typing import Optional
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Static
from textual.reactive import reactive
from textual.containers import Horizontal
from models import Track


class TrackItem(ListItem):
    DEFAULT_CSS = """
    TrackItem {
        padding: 0 1;
        height: 4;
    }
    TrackItem:hover { background: $surface-lighten-1; }
    TrackItem.--highlight { background: $accent-darken-2; }
    TrackItem .track-title { color: $text; }
    TrackItem .track-artist { color: $text-muted; }
    TrackItem .track-meta  { color: $text-muted; }
    TrackItem .track-dur   { color: $accent; dock: right; width: 6; }
    TrackItem .now-playing { color: $success; width: 2; }
    """

    def __init__(self, track: Track, is_playing: bool = False) -> None:
        super().__init__()
        self.track = track
        self._playing = is_playing

    def compose(self) -> ComposeResult:
        icon = "♫ " if self._playing else "  "
        yield Label(icon, classes="now-playing")
        from textual.containers import Vertical
        with Vertical():
            yield Label(self.track.title, classes="track-title")
            yield Label(self.track.artist, classes="track-artist")
            # Display metadata: plays, likes, date, genre
            meta_parts = []
            if self.track.play_count > 0:
                meta_parts.append(f"▶ {self.track.play_count_str}")
            if self.track.likes_count > 0:
                meta_parts.append(f"♥ {self.track.likes_count_str}")
            if self.track.created_date_str:
                meta_parts.append(self.track.created_date_str)
            if self.track.genre:
                meta_parts.append(f"[{self.track.genre}]")
            
            meta_text = " · ".join(meta_parts) if meta_parts else "No metadata"
            yield Label(meta_text, classes="track-meta")
        yield Label(self.track.duration_str, classes="track-dur")


class TrackList(ListView):
    DEFAULT_CSS = """
    TrackList {
        border: solid $primary-darken-2;
        background: $surface;
        height: 1fr;
    }
    TrackList > .loading {
        padding: 1 2;
        color: $text-muted;
    }
    """

    _current_playing_id: reactive[Optional[str]] = reactive(None)

    def show_loading(self) -> None:
        self.clear()
        self.mount(ListItem(Label("  Searching…", classes="loading")))

    def show_empty(self, msg: str = "No results found.") -> None:
        self.clear()
        self.mount(ListItem(Label(f"  {msg}", classes="loading")))

    def populate(self, tracks: list[Track], playing_id: Optional[str] = None) -> None:
        self.clear()
        for track in tracks:
            self.mount(TrackItem(track, is_playing=(track.id == playing_id)))

    @property
    def selected_track(self) -> Optional[Track]:
        item = self.highlighted_child
        if isinstance(item, TrackItem):
            return item.track
        return None
