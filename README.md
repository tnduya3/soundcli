# soundcli 🎵

A SoundCloud terminal music player with a rich TUI — search, queue, and control playback without leaving the terminal.

```
┌────────────────────────────────────────────────────────────────┐
│  soundcli                                          12:34:56     │
├────────────────────────────────────────────────────────────────┤
│  🔍  Search SoundCloud…                                        │
├──────────────────────────────────┬─────────────────────────────┤
│  RESULTS                         │  QUEUE                      │
│  ▶ Tame Impala - Let It Happen   │  1. track name              │
│    Flume - Never Be Like You     │  2. another track           │
│    Bonobo - Kong                 │                             │
├──────────────────────────────────┴─────────────────────────────┤
│  ♫  Tame Impala — Let It Happen                                │
│  ━━━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━━━  2:34 / 7:47            │
│  [F] Search  [Space] Play/Pause  [N] Next  [↑↓] Volume         │
│  ▶ Playing · 7:47                                    VOL: 80 🔊 │
└────────────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.11+
- `mpv` media player (handles all audio decoding & streaming)

## Install

```bash
# 1. Install mpv
brew install mpv          # macOS
sudo apt install mpv      # Ubuntu/Debian
choco install mpv         # Windows

# 2. Clone / download the project
cd soundcli

# 3. Create virtual environment
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Run!
python main.py
```

## Keybindings

| Key | Action |
|-----|--------|
| `F` | Focus search bar |
| `Enter` | Play selected track |
| `Space` | Toggle pause |
| `N` | Next track in queue |
| `A` | Add selected track to queue |
| `←` / `→` | Seek back / forward 10s |
| `↑` / `↓` | Volume up / down |
| `Q` | Quit |

## How It Works

1. **Search** — Queries the SoundCloud public API (`api-v2.soundcloud.com`) using a scraped `client_id`
2. **Stream resolution** — Each track's transcoding URL is resolved to a real CDN `.mp3` / HLS URL
3. **Playback** — `mpv` runs as a subprocess with an IPC socket for real-time control
4. **TUI** — Built with [Textual](https://github.com/Textualize/textual) for reactive, async UI updates
5. **Config** — Volume and history are persisted to `~/.config/soundcli/config.json`

## Notes

- SoundCloud's `client_id` is scraped from their web JS bundle on first run. If it fails, a known fallback is used.
- On Windows, the IPC socket path uses a named pipe (`\\.\pipe\soundcli-mpv`) — ensure mpv is in your PATH.
- Seeking and volume work via mpv's JSON IPC protocol over a Unix socket.
