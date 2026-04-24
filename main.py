#!/usr/bin/env python3
"""
SoundCLI — Entry point
Usage:
    python main.py
    python main.py --demo      (offline demo, no network or mpv needed)
"""
import sys

def main_entry():
    """Entry point for console script"""
    # Force demo mode before app imports so the service is swapped early
    if "--demo" in sys.argv:
        import services.soundcloud as _sc_mod
        _sc_mod._sc = _sc_mod.DemoSoundCloudService()

    from app import SoundCLI

    app = SoundCLI()
    app.run()

if __name__ == "__main__":
    main_entry()
