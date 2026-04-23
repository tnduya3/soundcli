from __future__ import annotations
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Static
from textual.containers import Vertical
from models import Track


class QueuePanel(Vertical):
    DEFAULT_CSS = """
    QueuePanel {
        border: solid $primary-darken-2;
        background: $surface;
        width: 30;
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
    QueuePanel ListView {
        background: $surface;
        border: none;
        height: 1fr;
    }
    QueuePanel ListItem {
        padding: 0 1;
        height: 3;
    }
    QueuePanel .q-title { color: $text; }
    QueuePanel .q-artist { color: $text-muted; }
    QueuePanel .q-empty { color: $text-muted; padding: 1 1; }
    QueuePanel .q-index { color: $accent; width: 3; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queue: list[Track] = []

    def compose(self) -> ComposeResult:
        yield Label("  ☰ Queue", classes="queue-header")
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
        self._refresh_list()

    @property
    def queue(self) -> list[Track]:
        return list(self._queue)

    def _refresh_list(self) -> None:
        lv = self.query_one("#queue-list", ListView)
        lv.clear()
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
