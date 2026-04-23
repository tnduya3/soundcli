"""
SoundCLI — Textual TUI for SoundCloud
"""
from __future__ import annotations

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Header, ListView, ListItem
from textual import work, on

import os
import config as cfg_module
from models import Track
from services.player import MPVPlayer
from components.search_bar import SearchBar
from components.track_list import TrackList, TrackItem
from components.queue_panel import QueuePanel
from components.player_bar import PlayerBar

_cfg = cfg_module.load()
if os.environ.get("SC_CLIENT_ID"):
    _cfg["sc_client_id"] = os.environ.get("SC_CLIENT_ID")
if os.environ.get("SC_AUTH_TOKEN"):
    _cfg["sc_auth_token"] = os.environ.get("SC_AUTH_TOKEN")
cfg_module.save(_cfg)

# Try real SC service; fall back to demo if setup fails.
# _sc_init_error is shown in the status bar on startup so the user knows why.
_sc_init_error: str = ""
try:
    from services.soundcloud import SoundCloudService
    _sc = SoundCloudService(client_id=_cfg.get("sc_client_id"), auth_token=_cfg.get("sc_auth_token"))
except Exception as _e:
    from services.soundcloud import DemoSoundCloudService
    _sc = DemoSoundCloudService()
    _sc_init_error = str(_e)


class SoundCLI(App):
    """Main application."""

    # Provide a custom theme using the desired red, white, dark grey palette
    CSS = """
    $accent: #cc241d;
    $accent-darken-2: #8a1712;
    $surface: #252526;
    $surface-lighten-1: #2d2d2d;
    $primary-darken-3: #1e1e1e;
    $text: #f9f9f9;
    $text-muted: #888888;
    $success: #cc241d;

    Screen {
        background: #121212;
    }
    Header {
        background: #1e1e1e;
        color: #f9f9f9;
        height: 2;
    }
    .main-area {
        height: 1fr;
    }
    .left-panel {
        width: 1fr;
        height: 1fr;
    }
    .results-label {
        height: 2;
        padding: 0 1;
        background: #1e1e1e;
        color: #cc241d;
        content-align: left middle;
        text-style: bold;
    }
    .status-bar {
        height: 1;
        background: #2d2d2d;
        padding: 0 2;
        color: #cccccc;
        content-align: left middle;
    }
    """

    BINDINGS = [
        Binding("/",     "focus_search",   "Search",     show=False),
        Binding("space", "play_pause",     "Play/Pause", show=False),
        Binding("a",     "queue_selected", "Add Queue",  show=False),
        Binding("j",     "next_track",     "Next",       show=False),
        Binding("k",     "prev_track",     "Restart",    show=False),
        Binding("l",     "like_selected",  "Like",       show=False),
        Binding("+",     "vol_up",         "Vol+",       show=False),
        Binding("=",     "vol_up",         "Vol+",       show=False),
        Binding("-",     "vol_down",       "Vol-",       show=False),
        Binding("\\",    "toggle_queue",   "Toggle Queue",show=False),
        Binding("r",     "toggle_repeat",  "Repeat Track",show=False),
        Binding("q",     "quit",           "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config = cfg_module.load()
        self._player = MPVPlayer()
        self._player._volume = self._config.get("volume", 70)
        self._player.on_position_change = self._on_position
        self._player.on_track_end = self._on_track_end
        self._current_track: Optional[Track] = None
        self._search_results: list[Track] = []
        self._repeat_track: bool = False
        self._sc = _sc

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield SearchBar()
        with Horizontal(classes="main-area"):
            with Vertical(classes="left-panel"):
                yield Label("  Results", classes="results-label", id="results-label")
                yield TrackList(id="track-list")
            yield QueuePanel(id="queue-panel")
        yield PlayerBar(id="player-bar")
        yield Label(
            "  Ready  |  Enter/click to play  |  Press / to search  |  Press \\ to toggle queue",
            classes="status-bar",
            id="status",
        )

    def on_mount(self) -> None:
        vol = self._config.get("volume", 70)
        self._player._volume = vol
        self.query_one(PlayerBar).update_volume(vol)
        self.query_one("#search-input", Input).focus()
        if _sc_init_error:
            self._set_status(
                f"[DEMO MODE] SoundCloud unavailable: {_sc_init_error.splitlines()[0]}"
            )
        else:
            self._set_status("Connected to SoundCloud — press / to search.")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        # Move focus to track list so Enter immediately plays
        self.query_one(TrackList).focus()
        self._do_search(query)

    @work(exclusive=True)
    async def _do_search(self, query: str) -> None:
        tl = self.query_one(TrackList)
        tl.show_loading()
        self._set_status(f"Searching for '{query}'...")
        try:
            results = await self._sc.search(query, limit=25)
            self._search_results = results
            playing_id = self._current_track.id if self._current_track else None
            tl.populate(results, playing_id=playing_id)
            self.query_one("#results-label", Label).update(
                f"  Results  —  {len(results)} tracks  (Enter to play)"
            )
            self._set_status(
                f"Found {len(results)} tracks — use ↑↓ to navigate, Enter to play"
            )
        except Exception as e:
            tl.show_empty(f"Error: {e}")
            self._set_status(f"Search error: {e}")

    # ------------------------------------------------------------------
    # KEY FIX: Listen for ListView.Selected (fired by Enter on a list item)
    # The app-level "enter" binding never fires because ListView consumes
    # the key and emits this event instead.
    # ------------------------------------------------------------------

    @on(ListView.Selected, "#track-list")
    async def on_track_list_selected(self, event: ListView.Selected) -> None:
        """Fired when the user presses Enter on a TrackItem."""
        event.stop()
        if isinstance(event.item, TrackItem):
            self._play_track(event.item.track)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    @work(exclusive=False)
    async def _play_track(self, track: Track) -> None:
        self._set_status(f"Loading: {track.display_title}...")
        pb = self.query_one(PlayerBar)
        pb.update_track(track, paused=False)
        try:
            stream_url = await self._sc.get_stream_url(track)
            track.stream_url = stream_url
            await self._player.play(stream_url)
            self._current_track = track
            pb.update_track(track, paused=False)
            self._set_status(f"Now playing: {track.display_title}")
            cfg_module.add_to_history(
                self._config,
                {"id": track.id, "title": track.title, "artist": track.artist},
            )
            cfg_module.save(self._config)
            tl = self.query_one(TrackList)
            tl.populate(self._search_results, playing_id=track.id)
        except Exception as e:
            self._set_status(f"Playback error: {e}")
            pb.update_track(None)

    def _on_position(self, pos: float, dur: float) -> None:
        self.call_later(self.query_one(PlayerBar).update_position, pos, dur)

    def _on_track_end(self) -> None:
        self.call_later(self._auto_next)

    def _auto_next(self) -> None:
        if self._repeat_track and self._current_track:
            self._play_track(self._current_track)
            return
            
        qp = self.query_one(QueuePanel)
        next_track = qp.pop_next()
        if next_track:
            self._play_track(next_track)
        else:
            self._current_track = None
            self.query_one(PlayerBar).update_track(None)
            self._set_status("Queue finished.")

    # ------------------------------------------------------------------
    # Key actions
    # ------------------------------------------------------------------

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    async def action_play_pause(self) -> None:
        if not self._player.is_playing:
            return
        await self._player.pause()
        paused = self._player.is_paused
        self.query_one(PlayerBar).update_track(self._current_track, paused=paused)
        status = "Paused" if paused else f"Resumed: {self._current_track.display_title}"
        self._set_status(status)

    def action_queue_selected(self) -> None:
        track = self.query_one(TrackList).selected_track
        if track:
            self.query_one(QueuePanel).add_track(track)
            self._set_status(f"Added to queue: {track.display_title}")

    async def action_next_track(self) -> None:
        next_track = self.query_one(QueuePanel).pop_next()
        if next_track:
            self._play_track(next_track)
        else:
            self._set_status("Queue is empty.")

    async def action_prev_track(self) -> None:
        if self._player.is_playing:
            await self._player.seek(0)
            self._set_status("Restarted track.")

    def action_like_selected(self) -> None:
        track = self.query_one(TrackList).selected_track
        if not track:
            return
        liked: list = self._config.setdefault("liked_ids", [])
        if track.id in liked:
            liked.remove(track.id)
            self._set_status(f"Unliked: {track.display_title}")
        else:
            liked.append(track.id)
            self._set_status(f"Liked: {track.display_title}")
        cfg_module.save(self._config)

    async def action_vol_up(self) -> None:
        new_vol = min(100, self._player.volume + 5)
        await self._player.set_volume(new_vol)
        self._config["volume"] = new_vol
        cfg_module.save(self._config)
        self.query_one(PlayerBar).update_volume(new_vol)

    async def action_vol_down(self) -> None:
        new_vol = max(0, self._player.volume - 5)
        await self._player.set_volume(new_vol)
        self._config["volume"] = new_vol
        cfg_module.save(self._config)
        self.query_one(PlayerBar).update_volume(new_vol)

    def action_toggle_queue(self) -> None:
        qp = self.query_one(QueuePanel)
        if qp.styles.display == "none":
            qp.styles.display = "block"
            self._set_status("Queue panel shown.")
        else:
            qp.styles.display = "none"
            self._set_status("Queue panel hidden.")

    def action_toggle_repeat(self) -> None:
        self._repeat_track = not self._repeat_track
        status = "enabled" if self._repeat_track else "disabled"
        self._set_status(f"Repeat track is now {status}.")
        self.query_one(PlayerBar).update_repeat(self._repeat_track)

    async def action_quit(self) -> None:
        await self._player.stop()
        cfg_module.save(self._config)
        self.exit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Label).update(f"  {msg}")