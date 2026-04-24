from __future__ import annotations
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Static
from textual.containers import Vertical, Horizontal
from models import Track


class QueuePanel(Vertical):
    DEFAULT_CSS = """
    QueuePanel {
        border: solid $primary-darken-2;
        background: $surface;
        width: 32;
        height: 1fr;
    }
    QueuePanel .queue-header {
        background: $primary-darken-3;
        padding: 0 1;
        height: 2;
        content-align: left middle;
        color: $accent;
        text-style: bold;
    }
    QueuePanel .queue-hints {
        background: $primary-darken-3;
        padding: 0 1;
        height: 2;
        color: $text-muted;
        content-align: left middle;
    }
    QueuePanel ListView {
        background: $surface;
        border: none;
        height: 1fr;
    }
    QueuePanel ListItem {
        padding: 0 1;
        height: 3;
    }
    QueuePanel ListItem:hover { background: $surface-lighten-1; }
    QueuePanel .q-title { color: $text; }
    QueuePanel .q-artist { color: $text-muted; }
    QueuePanel .q-empty { color: $text-muted; padding: 1 1; }
    QueuePanel .q-index { color: $accent; width: 3; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queue: list[Track] = []
        self._selected_idx: int = -1

    def compose(self) -> ComposeResult:
        yield Label("  ☰ Queue (0)", classes="queue-header", id="queue-header")
        yield Label("  ↑/↓ Move  |  del Delete  |  c Clear", classes="queue-hints")
        yield ListView(id="queue-list")

    def add_track(self, track: Track) -> None:
        self._queue.append(track)
        self._refresh_list()

    def pop_next(self) -> Track | None:
        if self._queue:
            t = self._queue.pop(0)
            self._refresh_list()
            return t
        return None

    def clear_queue(self) -> None:
        self._queue.clear()
        self._selected_idx = -1
        self._refresh_list()
    
    def move_item_up(self) -> None:
        """Move selected queue item up."""
        lv = self.query_one("#queue-list", ListView)
        if not lv.children:
            return
        idx = lv.index
        if idx > 0:
            self._queue[idx - 1], self._queue[idx] = self._queue[idx], self._queue[idx - 1]
            self._refresh_list()
            lv.index = idx - 1
    
    def move_item_down(self) -> None:
        """Move selected queue item down."""
        lv = self.query_one("#queue-list", ListView)
        if not lv.children:
            return
        idx = lv.index
        if idx < len(self._queue) - 1:
            self._queue[idx], self._queue[idx + 1] = self._queue[idx + 1], self._queue[idx]
            self._refresh_list()
            lv.index = idx + 1
    
    def remove_selected(self) -> None:
        """Remove the selected item from queue."""
        lv = self.query_one("#queue-list", ListView)
        if not lv.children or len(self._queue) == 0:
            return
        idx = lv.index
        if 0 <= idx < len(self._queue):
            self._queue.pop(idx)
            self._refresh_list()
            # Keep selection on same index if possible, or move up
            if lv.children:
                lv.index = min(idx, len(self._queue) - 1)

    @property
    def queue(self) -> list[Track]:
        return list(self._queue)

    def _refresh_list(self) -> None:
        lv = self.query_one("#queue-list", ListView)
        lv.clear()
        
        # Update header with queue count
        header = self.query_one("#queue-header", Label)
        header.update(f"  ☰ Queue ({len(self._queue)})")
        
        if not self._queue:
            lv.mount(ListItem(Label("  Queue is empty", classes="q-empty")))
            return
        for i, track in enumerate(self._queue, 1):
            item = ListItem(
                Label(f"{i}.", classes="q-index"),
                Vertical(
                    Label(track.title, classes="q-title"),
                    Label(track.artist, classes="q-artist"),
                )
            )
            lv.mount(item)
