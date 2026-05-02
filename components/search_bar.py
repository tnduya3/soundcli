from textual.app import ComposeResult
from textual.widgets import Input, Static
from textual.containers import Horizontal


class SearchBar(Horizontal):
    DEFAULT_CSS = """
    SearchBar {
        height: 3;
        padding: 0 1;
        margin: 1 1;
        background: $surface;
        border: heavy $accent-darken-2;
        align: left middle;
    }
    SearchBar .search-icon {
        width: 10;
        color: $success;
        content-align: center middle;
        height: 1;
        text-style: bold;
    }
    SearchBar Input {
        border: none;
        background: transparent;
        height: 1;
        width: 1fr;
        color: $text;
    }
    SearchBar Input:focus {
        border: none;
        background: transparent;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("[█▒ SEARCH]", classes="search-icon")
        yield Input(placeholder="Search SoundCloud... (press / to focus)", id="search-input")
