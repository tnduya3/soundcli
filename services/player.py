"""
MPV-based audio player.
Communicates with mpv via its JSON IPC socket for real-time control.
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import subprocess
import tempfile
from typing import Callable, Optional


class PlayerError(Exception):
    pass


class MPVPlayer:
    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._socket_path = self._make_socket_path()
        self._volume: int = 70
        self._is_paused: bool = False
        self._current_url: Optional[str] = None

        self.on_position_change: Optional[Callable[[float, float], None]] = None
        self.on_track_end: Optional[Callable[[], None]] = None

        self._poll_task: Optional[asyncio.Task] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._ipc_connected = False

    async def play(self, url: str) -> None:
        await self.stop()
        self._current_url = url
        self._is_paused = False
        self._socket_path = self._make_socket_path()
        await self._launch_mpv(url)
        await asyncio.sleep(1.0)
        await self._connect_ipc()
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def pause(self) -> None:
        await self._send_command(["cycle", "pause"])
        self._is_paused = not self._is_paused

    async def seek(self, percent: float) -> None:
        await self._send_command(["seek", percent, "absolute-percent"])

    async def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, volume))
        await self._send_command(["set_property", "volume", self._volume])

    async def stop(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        self._ipc_connected = False
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
            self._writer = None
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self._current_url = None
        self._is_paused = False

    @property
    def is_playing(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def volume(self) -> int:
        return self._volume

    async def _launch_mpv(self, url: str) -> None:
        cmd = [
            "mpv", "--no-video", "--really-quiet",
            f"--volume={self._volume}",
            f"--input-ipc-server={self._socket_path}",
            url,
        ]
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            raise PlayerError(
                "mpv not found. Install it:\n"
                "  macOS:  brew install mpv\n"
                "  Ubuntu: sudo apt install mpv\n"
                "  Windows: choco install mpv"
            )

    async def _connect_ipc(self) -> None:
        self._ipc_connected = False
        for _ in range(15):
            try:
                if platform.system() != "Windows":
                    self._reader, self._writer = await asyncio.open_unix_connection(self._socket_path)
                    self._ipc_connected = True
                    return
            except (FileNotFoundError, ConnectionRefusedError):
                await asyncio.sleep(0.3)

    async def _send_command(self, cmd: list) -> Optional[dict]:
        if not self._ipc_connected or not self._writer:
            return None
        try:
            payload = json.dumps({"command": cmd}) + "\n"
            self._writer.write(payload.encode())
            await self._writer.drain()
            line = await asyncio.wait_for(self._reader.readline(), timeout=1.0)
            return json.loads(line.decode().strip())
        except Exception:
            return None

    async def _get_property(self, prop: str) -> Optional[float]:
        resp = await self._send_command(["get_property", prop])
        if resp and resp.get("error") == "success":
            return resp.get("data")
        return None

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(0.5)
                if self._proc and self._proc.poll() is not None:
                    self._current_url = None
                    self._is_paused = False
                    if self.on_track_end:
                        self.on_track_end()
                    break
                if not self._ipc_connected:
                    continue
                pos = await self._get_property("time-pos")
                dur = await self._get_property("duration")
                if pos is not None and dur is not None and self.on_position_change:
                    self.on_position_change(float(pos), float(dur))
            except asyncio.CancelledError:
                break
            except Exception:
                continue

    @staticmethod
    def _make_socket_path() -> str:
        if platform.system() == "Windows":
            return r"\\.\pipe\soundcli_mpv"
        return os.path.join(tempfile.gettempdir(), f"soundcli_mpv_{os.getpid()}.sock")
