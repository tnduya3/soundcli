from textual.app import ComposeResult
from textual.widgets import Input, Static
from textual.containers import Horizontal


class SearchBar(Horizontal):
    DEFAULT_CSS = """
    SearchBar {
        height: 3;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $primary-darken-2;
        align: left middle;
    }
    SearchBar .search-icon {
        width: 4;
        color: $accent;
        content-align: center middle;
        height: 3;
    }
    SearchBar Input {
        border: none;
        background: transparent;
        height: 1;
        width: 1fr;
    }
    SearchBar Input:focus {
        border: none;
        background: transparent;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("🗁", classes="search-icon")
        yield Input(placeholder="Search SoundCloud… (press / to focus)", id="search-input")
