#!/usr/bin/env python3
"""
tui/screens.py — Screen classes used by the TUI.

Moved from top-level `scripts/tui_screens.py` into the package.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from textual.screen import Screen
    from textual.binding import Binding
    from textual.containers import ScrollableContainer
    from textual.widgets import Header, Footer, Static
    from textual.app import ComposeResult
except ImportError:
    print("Textual not installed. Run: pip3 install textual --break-system-packages")
    raise


class OutputScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back"),
    ]

    def __init__(self, title: str, output: str) -> None:
        super().__init__()
        self._title = title
        self._output = output

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(Static(self._output, id="out"))
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._title
