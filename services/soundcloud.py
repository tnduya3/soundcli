"""
SoundCloud service using the soundcloud-v2 package.

Install:  pip install soundcloud-v2

If the auto client_id fetch is blocked, set the env variable:
    export SC_CLIENT_ID=<your_id>

To get a client_id manually:
  1. Open https://soundcloud.com in a browser
  2. Open DevTools → Network tab → filter by "client_id"
  3. Copy the value from any request URL
"""
from __future__ import annotations

import asyncio
import itertools
import os
from typing import Optional

import requests as _requests

from models import Track

try:
    import soundcloud as _sc_lib
    _SC_AVAILABLE = True
except ImportError:
    _SC_AVAILABLE = False


class SoundCloudError(Exception):
    pass


class SoundCloudService:
    def __init__(self, client_id: str = None, auth_token: str = None) -> None:
        if not _SC_AVAILABLE:
            raise SoundCloudError(
                "soundcloud-v2 is not installed.\n"
                "Run: pip install soundcloud-v2"
            )
        client_id = client_id or os.environ.get("SC_CLIENT_ID") or None
        auth_token = auth_token or os.environ.get("SC_AUTH_TOKEN") or None
        try:
            self._api = _sc_lib.SoundCloud(client_id=client_id, auth_token=auth_token)
        except Exception as e:
            raise SoundCloudError(
                f"Could not initialise SoundCloud client: {e}\n\n"
                "Set your client_id manually:\n"
                "  1. Open soundcloud.com in a browser\n"
                "  2. DevTools → Network → search for 'client_id' in any request\n"
                "  3. export SC_CLIENT_ID=<your_id>  then re-run"
            ) from e

    async def search(self, query: str, limit: int = 20) -> list[Track]:
        """
        Search SoundCloud for tracks.

        FIX: search_tracks() returns a *lazy paginating generator*.
        Calling list() on it fetches ALL pages (thousands of tracks) and
        hangs indefinitely. We use itertools.islice to stop after `limit`
        items — this consumes exactly one API page and returns immediately.
        """
        loop = asyncio.get_event_loop()
        try:
            raw = await loop.run_in_executor(
                None,
                lambda: list(
                    itertools.islice(
                        self._api.search_tracks(query),
                        limit
                    )
                )
            )
        except Exception as e:
            raise SoundCloudError(f"Search failed: {e}") from e

        tracks: list[Track] = []
        for item in raw:
            t = _to_track(item)
            if t:
                tracks.append(t)
        return tracks

    async def get_stream_url(self, track: Track) -> str:
        """
        Resolve a playable CDN stream URL for the given track.

        soundcloud-v2 Track objects don't have a get_stream_url() method.
        The correct approach:
          1. resolve() the track to get its media.transcodings list
          2. Pick the progressive MP3 transcoding (best mpv compat)
          3. GET that transcoding.url?client_id=X  → returns {"url": "https://cf-media..."}
          4. Return that CDN url to mpv
        """
        loop = asyncio.get_event_loop()
        try:
            sc_track = await loop.run_in_executor(
                None, lambda: self._api.resolve(track.permalink_url)
            )
        except Exception as e:
            raise SoundCloudError(f"resolve() failed for {track.permalink_url}: {e}") from e

        if sc_track is None:
            raise SoundCloudError(f"Track not found: {track.permalink_url}")

        # Pick the best transcoding: prefer progressive MP3, fall back to HLS
        transcoding = _pick_transcoding(sc_track)
        if transcoding is None:
            raise SoundCloudError("No playable transcoding found for this track.")

        # Fetch the actual CDN url from the transcoding endpoint
        try:
            track_auth = getattr(sc_track, "track_authorization", None)
            cdn_url = await loop.run_in_executor(
                None, lambda: _resolve_transcoding_url(transcoding.url, self._api.client_id, track_auth)
            )
        except Exception as e:
            raise SoundCloudError(f"Could not get CDN stream URL: {e}") from e

        return cdn_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_track(item) -> Optional[Track]:
    """Convert a soundcloud-v2 Track object to our internal Track model."""
    try:
        artist = getattr(item.user, "username", None) or "Unknown"
        return Track(
            id=str(item.id),
            title=item.title or "Unknown",
            artist=artist,
            duration_ms=int(item.full_duration or item.duration or 0),
            permalink_url=item.permalink_url,
            artwork_url=getattr(item, "artwork_url", None),
            play_count=int(getattr(item, "play_count", 0) or 0),
            likes_count=int(getattr(item, "likes_count", 0) or 0),
            created_at=getattr(item, "created_at", None),
            genre=getattr(item, "genre", None),
        )
    except Exception:
        return None


def _pick_transcoding(sc_track):
    """
    Pick the best transcoding from a resolved track.
    Preference order:
      1. protocol=progressive  mime_type contains mpeg  (direct MP3 — best for mpv)
      2. protocol=progressive  any mime                 (direct stream)
      3. protocol=hls          mime_type contains mpeg  (HLS MP3 — mpv handles this too)
      4. Any transcoding at all
    """
    try:
        transcodings = list(sc_track.media.transcodings)
    except (AttributeError, TypeError):
        return None

    if not transcodings:
        return None

    def score(t):
        snipped = getattr(t, "snipped", False)
        proto = getattr(t.format, "protocol", "")
        mime  = getattr(t.format, "mime_type", "")
        
        penalty = 100 if snipped else 0
        
        if proto == "progressive" and "mpeg" in mime:
            return penalty + 0
        if proto == "progressive":
            return penalty + 1
        if proto == "hls" and "mpeg" in mime:
            return penalty + 2
        return penalty + 3

    return sorted(transcodings, key=score)[0]


def _resolve_transcoding_url(transcoding_url: str, client_id: str, track_auth: str = None) -> str:
    """
    GET the transcoding endpoint to get the real CDN URL.
    Response JSON: {"url": "https://cf-media.sndcdn.com/..."}
    """
    params = {"client_id": client_id}
    if track_auth:
        params["track_authorization"] = track_auth
        
    resp = _requests.get(
        transcoding_url,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    url = data.get("url")
    if not url:
        raise SoundCloudError(f"No url in transcoding response: {data}")
    return url


# ---------------------------------------------------------------------------
# Demo / offline fallback
# ---------------------------------------------------------------------------

DEMO_TRACKS = [
    Track("d1", "Midnight City",   "M83",           243000, play_count=12500000, likes_count=85000, created_at="2011-09-20T00:00:00Z", genre="Electronic"),
    Track("d2", "Intro",           "The xx",        128000, play_count=8300000, likes_count=52000, created_at="2009-02-03T00:00:00Z", genre="Indie"),
    Track("d3", "Crystalised",     "The xx",        213000, play_count=15200000, likes_count=98000, created_at="2009-08-10T00:00:00Z", genre="Indie"),
    Track("d4", "Bad Guy",         "Billie Eilish", 194000, play_count=892000000, likes_count=2100000, created_at="2018-03-29T00:00:00Z", genre="Pop"),
    Track("d5", "Blinding Lights", "The Weeknd",    200000, play_count=750000000, likes_count=1800000, created_at="2019-11-29T00:00:00Z", genre="Synthwave"),
    Track("d6", "Sunflower",       "Post Malone",   158000, play_count=580000000, likes_count=1200000, created_at="2018-08-03T00:00:00Z", genre="Hip-Hop"),
    Track("d7", "Levitating",      "Dua Lipa",      203000, play_count=650000000, likes_count=1500000, created_at="2020-10-23T00:00:00Z", genre="Disco-Pop"),
    Track("d8", "Heat Waves",      "Glass Animals", 238000, play_count=490000000, likes_count=1100000, created_at="2020-06-19T00:00:00Z", genre="Indie"),
]


class DemoSoundCloudService:
    """Offline demo — returns fake tracks; no network or SC account needed."""

    async def search(self, query: str, limit: int = 20) -> list[Track]:
        await asyncio.sleep(0.4)
        q = query.lower()
        results = [
            t for t in DEMO_TRACKS
            if q in t.title.lower() or q in t.artist.lower()
        ] or DEMO_TRACKS
        return results[:limit]

    async def get_stream_url(self, track: Track) -> str:
        raise SoundCloudError("Demo mode — no real stream URLs available.")