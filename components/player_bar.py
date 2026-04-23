from __future__ import annotations
import random
from typing import Optional, Any
from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.widget import Widget
from rich.text import Text
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from models import Track


def _fmt(sec: float) -> str:
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"


def _vol_bar(vol: int) -> str:
    filled = round(vol / 10)
    return "█" * filled + "░" * (10 - filled)


class StringProgressBar(Widget):
    DEFAULT_CSS = """
    StringProgressBar {
        width: 1fr;
        height: 1;
        color: $accent;
        content-align: center middle;
        margin: 0 1;
    }
    """
    pct = reactive(0.0)

    def render(self) -> Text:
        # Provide a fallback width if the size hasn't fully computed yet
        w = max(self.size.width - 2, 20)
        filled = round((self.pct / 100) * w)
        bar = "━" * filled + "─" * (w - filled)
        return Text(f" {bar} ")


class PlayerBar(Vertical):
    DEFAULT_CSS = """
    PlayerBar {
        height: 7;
        background: $primary-darken-3;
        border-top: solid $accent;
        padding: 0 2;
    }
    PlayerBar .now-playing-label {
        color: $accent;
        text-style: bold;
        height: 2;
        content-align: left middle;
        padding-top: 1;
    }
    PlayerBar .progress-row {
        height: 2;
        width: 1fr;
        align: left middle;
    }
    PlayerBar .bar-label {
        width: 1fr;
        margin: 0 1;
        color: $accent;
        content-align: center middle;
    }
    PlayerBar .time-label {
        color: $text-muted;
        width: 12;
    }
    PlayerBar #pos-label {
        content-align: right middle;
    }
    PlayerBar #dur-label {
        content-align: left middle;
    }
    PlayerBar .controls-row {
        height: 2;
        align: left middle;
    }
    PlayerBar .controls {
        width: 30;
        color: $text;
        content-align: left middle;
    }
    PlayerBar .vol-label {
        width: 30;
        color: $text-muted;
        content-align: left middle;
    }
    PlayerBar .hint-label {
        width: 1fr;
        color: $text-muted;
        content-align: right middle;
    }
    """

    _track: reactive[Optional[Track]] = reactive(None)
    _pos_sec: reactive[float] = reactive(0.0)
    _dur_sec: reactive[float] = reactive(0.0)
    _paused: reactive[bool] = reactive(False)
    _volume: reactive[int] = reactive(70)
    _eq_frames: list[str] = [" ▂▃▄▅", "▂▃▄▅▆", "▃▄▅▆▇", "▄▅▆▇█", "▅▆▇█▇", "▆▇█▇▆", "▇█▇▆▅", "█▇▆▅▄", "▇▆▅▄▃", "▆▅▄▃▂", "▅▄▃▂ "]
    _eq_index: int = 0
    _eq_timer: Any = None
    _repeat: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Label("♫  Nothing playing", classes="now-playing-label", id="np-label")
        with Horizontal(classes="progress-row"):
            yield Label("0:00", classes="time-label", id="pos-label")
            yield StringProgressBar(id="progress-label")
            yield Label("0:00", classes="time-label", id="dur-label")
        with Horizontal(classes="controls-row"):
            yield Label("  [◀◀ k] [▷| space] [▶▶ j]", classes="controls", id="ctrl-label", markup=False)
            yield Label("🕪 ⚫█▀█▄▄𓂸  vol: 70", classes="vol-label", id="vol-label")
            yield Label("[/] search  [\\] toggle queue  [r] repeat: off  [a] queue  [l] like  [q] quit", classes="hint-label", id="hint-label", markup=False)

    def on_mount(self) -> None:
        self._eq_timer = self.set_interval(0.15, self._tick_eq, pause=True)

    def _tick_eq(self) -> None:
        self._eq_index = (self._eq_index + 1) % len(self._eq_frames)
        self._render_np()

    def _render_np(self) -> None:
        if self._track:
            if self._paused:
                icon = "▐▐"
            else:
                icon = f"[{self._eq_frames[self._eq_index]}] "
            self.query_one("#np-label", Label).update(f"{icon} {self._track.display_title}")
        else:
            self.query_one("#np-label", Label).update("♫  Nothing playing")

    # ------------------------------------------------------------------
    # Update methods called from app
    # ------------------------------------------------------------------

    def update_track(self, track: Optional[Track], paused: bool = False) -> None:
        self._track = track
        self._paused = paused
        if track and not paused:
            self._eq_timer.resume()
        else:
            self._eq_timer.pause()
            
        self._render_np()
        ctrl = "  [◀◀ k] [▷| space] [▶▶ j]" if not paused else "  [◀◀ k] [▷| space] [▶▶ j]"
        self.query_one("#ctrl-label", Label).update(ctrl)

    def update_repeat(self, repeat: bool) -> None:
        self._repeat = repeat
        status = "on" if repeat else "off"
        self.query_one("#hint-label", Label).update(f"[/] search  [\\] toggle queue  [r] repeat: {status}  [a] queue  [l] like  [q] quit")

    def update_position(self, pos_sec: float, dur_sec: float) -> None:
        self._pos_sec = pos_sec
        self._dur_sec = dur_sec
        pct = (pos_sec / dur_sec * 100) if dur_sec > 0 else 0
        
        self.query_one("#progress-label", StringProgressBar).pct = pct
        
        self.query_one("#pos-label", Label).update(_fmt(pos_sec))
        self.query_one("#dur-label", Label).update(_fmt(dur_sec))

    def on_resize(self) -> None:
        # Trigger a re-render when the terminal is resized
        bar = self.query_one("#progress-label", StringProgressBar)
        bar.refresh()

    def update_volume(self, vol: int) -> None:
        self._volume = vol
        self.query_one("#vol-label", Label).update(f"🕪 {_vol_bar(vol)}  vol: {vol}")
