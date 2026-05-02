from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

from textual.app import ComposeResult
from textual.widgets import Label
from textual.widget import Widget
from rich.text import Text
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from models import Track

# ---------------------------------------------------------------------------
# rich-pixels + Pillow — optional, graceful fallback if missing
# pip install rich-pixels Pillow
# ---------------------------------------------------------------------------
try:
    from rich_pixels import Pixels
    from PIL import Image as PILImage
    _PIXELS_AVAILABLE = True
except ImportError:
    _PIXELS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(sec: float) -> str:
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"


def _vol_bar(vol: int) -> str:
    filled = round(vol / 10)
    return "▓" * filled + "░" * (10 - filled)


# ---------------------------------------------------------------------------
# Asset paths — assets/ folder must sit next to player_bar.py
# ---------------------------------------------------------------------------
_ASSETS = Path(__file__).parent.parent / "assets"
AJAW_SLEEP_PATH  = _ASSETS / "ajaw_sleep.png"
AJAW_DANCE_PATHS = [
    _ASSETS / "ajaw_dance_1.png",
    _ASSETS / "ajaw_dance_2.png",
    _ASSETS / "ajaw_dance_3.png",
    _ASSETS / "ajaw_dance_4.png",
]

# HOW THE MATH WORKS:
#   rich-pixels uses half-block characters (▄/▀), so every 2 image pixels
#   tall = 1 terminal row.
#
#   Player bar slot is 7 rows tall  →  need AJAW_H = 7 * 2 = 14 pixels
#   CSS widget is 28 terminal cols wide  →  AJAW_W = 28 pixels (1 px = 1 col)
#
# If Ajaw looks too small/large, tune AJAW_W only (keep AJAW_H = 14 to
# preserve the 7-row fit). Dimensions must match CSS widget size for proper alignment.
AJAW_W = 28   # terminal columns (matches CSS widget width)
AJAW_H = 14   # terminal rows × 2  (= 7 visible rows)


# ---------------------------------------------------------------------------
# Fallback ASCII art (shown when images are unavailable)
# ---------------------------------------------------------------------------
_FALLBACK_SLEEP = (
    "     ( ☀ ) z      \n"
    "     (■ _ ■)      \n"
    "     /|▌|\\       \n"
    "     ╱ ██╲       \n"
    "    ╱╱   ╲╲      \n"
    "     |   |       \n"
    "     ⌒   ⌒      "
)
_FALLBACK_DANCE = [
    "    \\( ☀ )/ ♪   \n   ─(■ ▽ ■)─    \n    \\╲▌╱/       \n     \\  ██     \n     ╱╲╱  ╲     \n     ╱    ╲     \n    /──   ──\\   ",
    "    /( ☀ )\\ ♫   \n   ─(■ o ■)─    \n     /╲▌╱\\     \n     ╱  ██╲     \n    ╱╱  ╲╲╲     \n    /     \\     \n   ─╯     ╰─    ",
    "     ( ☀ )  ♩  \n    ─(■ ◡ ■)─   \n     /╲▌╱/      \n    ╱   ██╲     \n   ╱   ╱  ╲╲    \n       |   |    \n     ──┘   └──  ",
    "   * \\(☀)/  *  \n    ─(■▼■)─    \n     / ▌╲      \n     ╱ ██╲     \n    ╱╱   ╲╲    \n     |   |     \n    ─┘   └─    ",
]


# ---------------------------------------------------------------------------
# Image loader
# ---------------------------------------------------------------------------

def _load_pixels(path: Path, w: int, h: int) -> "Optional[Pixels]":
    """Load a PNG, resize to w×h pixels, return a Pixels renderable or None."""
    if not _PIXELS_AVAILABLE or not path.exists():
        return None
    try:
        with PILImage.open(path) as img:
            img = img.convert("RGBA")
            
            # Resize FIRST using high-quality LANCZOS to minimize color fringing
            img = img.resize((w, h), PILImage.LANCZOS)
            
            # Then clean up alpha channel to avoid color halos
            # Create a new RGBA image with clean transparency
            clean = PILImage.new("RGBA", img.size, (0, 0, 0, 0))
            px_src = img.load()
            px_dst = clean.load()
            
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = px_src[x, y]
                    # Keep only clearly opaque pixels; threshold rest to transparent
                    if a > 200:
                        px_dst[x, y] = (r, g, b, 255)
                    else:
                        px_dst[x, y] = (0, 0, 0, 0)
            
            return Pixels.from_image(clean)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# AjawWidget
# ---------------------------------------------------------------------------

class AjawWidget(Widget):
    """
    Renders Ajaw pixel art while playing, sleep frame when paused/idle.
    Falls back to Unicode art if rich-pixels or image files are missing.
    """

    DEFAULT_CSS = """
    AjawWidget {
        width: 28;
        height: 7;
        content-align: center middle;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._playing    = False
        self._frame_idx  = 0
        self._fb_idx     = 0
        self._timer: Any = None

        # Pre-load all frames at startup for smooth animation
        self._sleep_px: "Optional[Pixels]" = _load_pixels(AJAW_SLEEP_PATH, AJAW_W, AJAW_H)
        self._dance_px: "list[Optional[Pixels]]" = [
            _load_pixels(p, AJAW_W, AJAW_H) for p in AJAW_DANCE_PATHS
        ]
        self._has_images: bool = any(f is not None for f in self._dance_px)

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.4, self._tick, pause=True)

    def _tick(self) -> None:
        valid = [f for f in self._dance_px if f is not None]
        if valid:
            self._frame_idx = (self._frame_idx + 1) % len(valid)
        else:
            self._fb_idx = (self._fb_idx + 1) % len(_FALLBACK_DANCE)
        self.refresh()

    def set_playing(self, playing: bool) -> None:
        """Call from PlayerBar to start/stop animation."""
        self._playing = playing
        self._timer.resume() if playing else self._timer.pause()
        self.refresh()

    def render(self) -> Any:
        if self._playing:
            valid = [f for f in self._dance_px if f is not None]
            if valid:
                return valid[self._frame_idx % len(valid)]
            return Text(_FALLBACK_DANCE[self._fb_idx], style="bold yellow")
        else:
            if self._sleep_px is not None:
                return self._sleep_px
            return Text(_FALLBACK_SLEEP, style="bold yellow")


# ---------------------------------------------------------------------------
# StringProgressBar
# ---------------------------------------------------------------------------

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

    def watch_pct(self) -> None:
        self.refresh()

    def render(self) -> Text:
        w = max(self.size.width - 2, 20)
        filled = max(0, min(w, round((self.pct / 100) * w)))
        bar = "▓" * filled + "░" * (w - filled)
        return Text(f"[{bar}]", style="bold #00ffff", no_wrap=True, overflow="crop")


# ---------------------------------------------------------------------------
# PlayerBar
# ---------------------------------------------------------------------------

class PlayerBar(Vertical):
    DEFAULT_CSS = """
    PlayerBar {
        height: 9;
        background: $surface;
        border-top: heavy $success;
        padding: 0 2;
    }
    PlayerBar AjawWidget {
        width: 28;
        height: 7;
        content-align: center middle;
    }
    PlayerBar .player-controls-container {
        width: 1fr;
    }
    PlayerBar .now-playing-label {
        color: $accent;
        text-style: bold;
        height: 2;
        content-align: left middle;
        padding-top: 1;
    }
    PlayerBar .progress-row {
        height: 1;
        width: 1fr;
        align: left middle;
    }
    PlayerBar .time-label {
        color: $text-muted;
        width: 12;
    }
    PlayerBar #pos-label { content-align: right middle; }
    PlayerBar #dur-label { content-align: left middle; }
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

    _track:   reactive[Optional[Track]] = reactive(None)
    _pos_sec: reactive[float]           = reactive(0.0)
    _dur_sec: reactive[float]           = reactive(0.0)
    _paused:  reactive[bool]            = reactive(False)
    _volume:  reactive[int]             = reactive(70)
    _repeat:  reactive[bool]            = reactive(False)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield AjawWidget(id="ajaw-art")
            with Vertical(classes="player-controls-container"):
                yield Label("♫  Nothing playing", classes="now-playing-label", id="np-label")
                with Horizontal(classes="progress-row"):
                    yield Label("0:00", classes="time-label", id="pos-label")
                    yield StringProgressBar(id="progress-label")
                    yield Label("0:00", classes="time-label", id="dur-label")
                with Horizontal(classes="controls-row"):
                    yield Label(
                        "  [◀◀ k] [▷| space] [▶▶ j]",
                        classes="controls", id="ctrl-label", markup=False,
                    )
                    yield Label(
                        f"🕪 {_vol_bar(70)}",
                        classes="vol-label", id="vol-label",
                    )
                    yield Label(
                        "[/] search  [\\] queue  [r] repeat: off  [a] queue  [l] like  [q] quit",
                        classes="hint-label", id="hint-label", markup=False,
                    )

    def update_track(self, track: Optional[Track], paused: bool = False) -> None:
        self._track  = track
        self._paused = paused
        self.query_one("#ajaw-art", AjawWidget).set_playing(bool(track and not paused))
        if track:
            icon = "▐▐" if paused else "♫"
            self.query_one("#np-label", Label).update(f"{icon}  {track.display_title}")
            self.app.title = "SoundCLI [Paused]" if paused else "SoundCLI"
        else:
            self.query_one("#np-label", Label).update("♫  Nothing playing")
            self.app.title = "SoundCLI"

    def update_repeat(self, repeat: bool) -> None:
        self._repeat = repeat
        status = "on" if repeat else "off"
        self.query_one("#hint-label", Label).update(
            f"[/] search  [\\] queue  [r] repeat: {status}  [a] queue  [l] like  [q] quit"
        )

    def update_position(self, pos_sec: float, dur_sec: float) -> None:
        self._pos_sec = pos_sec
        self._dur_sec = dur_sec
        pct = (pos_sec / dur_sec * 100) if dur_sec > 0 else 0
        self.query_one("#progress-label", StringProgressBar).pct = pct
        self.query_one("#pos-label", Label).update(_fmt(pos_sec))
        self.query_one("#dur-label", Label).update(_fmt(dur_sec))

    def on_resize(self) -> None:
        bar = self.query_one("#progress-label", StringProgressBar)
        bar.refresh()  # Re-render progress bar to fit new width

    def update_volume(self, vol: int) -> None:
        self._volume = vol
        self.query_one("#vol-label", Label).update(f"🕪 {_vol_bar(vol)}  vol: {vol}")