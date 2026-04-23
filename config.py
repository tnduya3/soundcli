import json
import os
from pathlib import Path
from typing import Any


def _config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    p = base / "soundcli"
    p.mkdir(parents=True, exist_ok=True)
    return p / "config.json"


_DEFAULTS: dict[str, Any] = {
    "volume": 70,
    "liked_ids": [],
    "history": [],
}


def load() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return dict(_DEFAULTS)
    try:
        with open(path) as f:
            data = json.load(f)
        # Fill any missing keys with defaults
        for k, v in _DEFAULTS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(_DEFAULTS)


def save(cfg: dict[str, Any]) -> None:
    path = _config_path()
    try:
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def add_to_history(cfg: dict[str, Any], track_info: dict) -> None:
    history: list = cfg.setdefault("history", [])
    # Avoid duplicates at front
    history = [h for h in history if h.get("id") != track_info.get("id")]
    history.insert(0, track_info)
    cfg["history"] = history[:50]  # Keep last 50
