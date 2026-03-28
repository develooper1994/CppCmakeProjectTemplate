#!/usr/bin/env python3
"""
tui.py — Terminal User Interface for CppCmakeProjectTemplate tooling.

Requires: pip3 install textual --break-system-packages

Usage:
    python3 scripts/tui.py [--preset <preset>]
    # or via tool dispatcher:
    python3 scripts/tool.py tui [--preset <preset>]

Priority order for preset value:
    interactive (widget change) > --preset CLI arg > session file > default

Session is persisted to .session.json in project root (shared with `tool.py`).
All operations use DIRECT IMPORTS — no subprocess calls between Python modules.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, ScrollableContainer
    from textual.screen import Screen
    from textual.widgets import (
        Button, Footer, Header, Input, Label,
        Select, Static, TabbedContent, TabPane, Checkbox,
    )
except ImportError:
    print("Textual not installed. Run: pip3 install textual --break-system-packages")
    sys.exit(1)

# ── Path bootstrap ────────────────────────────────────────────────────────────
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import subprocess
import sys
import json
from pathlib import Path

# Use the `tool.py` dispatcher for all operations (no direct command imports)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOL_SCRIPT = PROJECT_ROOT / "scripts" / "tool.py"
TOOL_CMD_BASE = [sys.executable, str(TOOL_SCRIPT)]


def _run_tool_cmd(args_list: list[str]) -> tuple[str, int]:
    """Run `tool <args...>` and return (output, returncode)."""
    try:
        proc = subprocess.run(TOOL_CMD_BASE + args_list,
                              cwd=PROJECT_ROOT,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              check=False)
        out = proc.stdout or ""
        # Strip ANSI for TUI display
        import re
        out = re.sub(r'\x1b\[[0-9;]*m', '', out)
        return out.strip(), proc.returncode
    except Exception as e:
        return f"Exception invoking tool: {e}", 1

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PRESET = "gcc-debug-static-x86_64"


# ── Session helpers ───────────────────────────────────────────────────────────
# Priority: interactive (widget change) > CLI --preset arg > session file > default

def _initial_preset(cli_arg: str | None) -> str:
    """Resolve initial preset: CLI arg > session > default."""
    if cli_arg:
        return cli_arg
    out, rc = _run_tool_cmd(["session", "load", "--print"])
    if rc == 0 and out:
        try:
            sess = json.loads(out)
            return sess.get("last_preset", _DEFAULT_PRESET)
        except Exception:
            pass
    return _DEFAULT_PRESET


# ── Direct-call helpers (no subprocess) ──────────────────────────────────────

# All runtime tool operations are performed by invoking the `tool.py`
# dispatcher via subprocess using `_run_tool_cmd()` above. This keeps the
# TUI decoupled and allows `tool.py` plugins to be used without importing
# command modules directly into the TUI process.


# ── Output screen ─────────────────────────────────────────────────────────────

class OutputScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back"),
                Binding("q",      "app.pop_screen", "Back")]

    def __init__(self, title: str, output: str) -> None:
        super().__init__()
        self._title  = title
        self._output = output

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(Static(self._output, id="out"))
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._title


# ── Main App ──────────────────────────────────────────────────────────────────

class CppTemplateTUI(App):
    """CppCmakeProjectTemplate TUI — direct imports, no subprocess."""

    CSS = """
    Screen { background: $surface; }
    #main  { padding: 1 2; }
    #result {
        border: solid $primary;
        height: 1fr;
        padding: 1;
        overflow-y: scroll;
    }
    .section-title { color: $accent; text-style: bold; margin-bottom: 1; }
    .row  { height: auto; margin-bottom: 1; }
    Input  { margin-bottom: 1; }
    Select { margin-bottom: 1; }
    """

    BINDINGS = [
        Binding("q",      "quit",         "Quit"),
        Binding("ctrl+l", "clear_output", "Clear"),
    ]

    TITLE     = "CppCmakeProjectTemplate TUI"
    SUB_TITLE = "interactive > cli args > session"

    def __init__(self, initial_preset: str = _DEFAULT_PRESET) -> None:
        super().__init__()
        self._initial_preset = initial_preset
        self._plugin_name_map: dict[str, str] = {}
        # mapping widget id -> arg meta (name, type, required)
        self._plugin_arg_map: dict[str, dict] = {}

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():

            # Build tab
            with TabPane("🔨 Build", id="tab-build"):
                with Vertical(id="main"):
                    yield Label("Build Operations", classes="section-title")
                    # Populate options dynamically from CMakePresets.json on mount
                    yield Select(options=[], allow_blank=True, id="build-preset")
                    with Horizontal(classes="row"):
                        yield Button("▶ Build",      id="btn-build",     variant="primary")
                        yield Button("✔ Check",      id="btn-check",     variant="success")
                        yield Button("🗑 Clean",     id="btn-clean")
                        yield Button("🗑 Clean All", id="btn-clean-all")
                        yield Button("📦 Extension", id="btn-extension")
                    yield Static("", id="result")

            # Libraries tab
            with TabPane("📚 Libraries", id="tab-libs"):
                with Vertical(id="main"):
                    yield Label("Library Management", classes="section-title")
                    with Horizontal(classes="row"):
                        yield Button("📋 List",   id="btn-lib-list")
                        yield Button("🌳 Tree",   id="btn-lib-tree")
                        yield Button("🩺 Doctor", id="btn-lib-doctor", variant="warning")

                    yield Label("Add Library:")
                    yield Input(placeholder="name (lowercase_underscore)", id="lib-name")
                    with Horizontal(classes="row"):
                        yield Select(
                            options=[("Normal","normal"),("Header-only","header-only"),
                                     ("Interface","interface")],
                            allow_blank=False, id="lib-type",
                        )
                        yield Select(
                            options=[("No template",""),("Singleton","singleton"),
                                     ("Pimpl","pimpl"),("Observer","observer"),("Factory","factory")],
                            allow_blank=False, id="lib-template",
                        )
                    yield Input(placeholder="deps (comma-separated, optional)", id="lib-deps")
                    with Horizontal(classes="row"):
                        yield Button("➕ Add",     id="btn-lib-add",    variant="primary")
                        yield Button("🔍 Dry-run", id="btn-lib-dry")

                    yield Label("Remove Library:")
                    yield Input(placeholder="library name to remove", id="lib-remove-name")
                    with Horizontal(classes="row"):
                        yield Button("🗑 Remove (detach)",  id="btn-lib-remove")
                        yield Button("💥 Remove + Delete", id="btn-lib-delete", variant="error")

                    yield Label("Export (find_package support):")
                    yield Input(placeholder="library name", id="lib-export-name")
                    yield Button("📤 Export", id="btn-lib-export", variant="success")
                    yield Static("", id="result")

            # Project tab
            with TabPane("⚙ Project", id="tab-project"):
                with Vertical(id="main"):
                    yield Label("Project Orchestration", classes="section-title")
                    with Horizontal(classes="row"):
                        yield Button("📋 Targets",    id="btn-target-list")
                        yield Button("📋 Presets",    id="btn-preset-list")
                        yield Button("🔧 Toolchains", id="btn-tc-list")
                        yield Button("🌐 Repo",       id="btn-repo-list")
                        yield Button("📊 Versions",   id="btn-repo-versions")

                    yield Label("C++ Standard (solution-wide):")
                    with Horizontal(classes="row"):
                        yield Select(
                            options=[("C++14","14"),("C++17","17"),
                                     ("C++20","20"),("C++23","23")],
                            allow_blank=False, id="std-select",
                        )
                        yield Button("⬆ Upgrade Std", id="btn-upgrade-std", variant="primary")

                    yield Label("Config key / value:")
                    with Horizontal(classes="row"):
                        yield Input(placeholder="key (e.g. ENABLE_ASAN)", id="cfg-key")
                        yield Input(placeholder="value (e.g. ON)",        id="cfg-val")
                        yield Button("Set", id="btn-cfg-set", variant="primary")

                    with Horizontal(classes="row"):
                        yield Button("🩺 Doctor", id="btn-sol-doctor", variant="warning")
                        yield Button("🚀 CI",     id="btn-ci",         variant="success")
                    yield Static("", id="result")

            # Info tab
            with TabPane("ℹ Info", id="tab-info"):
                with Vertical(id="main"):
                    yield Label("Library Info & Tests", classes="section-title")
                    yield Input(placeholder="library name", id="info-lib-name")
                    with Horizontal(classes="row"):
                        yield Button("🔍 Info",       id="btn-info-lib")
                        yield Button("▶ Run Tests",   id="btn-info-test", variant="success")
                    yield Static("", id="result")

            # Plugins tab
            with TabPane("🔌 Plugins", id="tab-plugins"):
                with Vertical(id="main"):
                    yield Label(content="Discovered Plugins", classes="section-title")
                    yield Select(options=[], allow_blank=True, id="plugins-select")
                    with Vertical(id="plugin-args-container"):
                        yield Input(placeholder="args (space-separated)", id="plugin-args-fallback")
                    yield Static("", id="plugin-desc")
                    with ScrollableContainer(id="plugins-list-container"):
                        with Vertical(id="plugins-buttons"):
                            pass
                    with Horizontal(classes="row"):
                        yield Button("▶ Run Plugin", id="btn-plugin-run", variant="primary")
                        yield Button("🔄 Refresh", id="btn-plugin-refresh")
                    yield Static("", id="result")

        yield Footer()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        # Populate build presets from CMakePresets.json and set initial value
        try:
            try:
                self._populate_build_presets()
            except Exception:
                pass
            sel = self.query_one("#build-preset", Select)
            # Try to set the value to the resolved initial preset
            try:
                opts = getattr(sel, "options", None) or getattr(sel, "_options", None) or []
                valid = [v for _, v in opts]
                if self._initial_preset in valid:
                    try:
                        sel.value = self._initial_preset
                    except Exception:
                        # fallback: set to label if that matches
                        try:
                            first_label = next((lbl for lbl, val in opts if val == self._initial_preset), None)
                            if first_label is not None:
                                sel.value = first_label
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass
        # Populate plugin list on startup
        try:
            self._refresh_plugins()
        except Exception:
            pass

    def _refresh_plugins(self) -> None:
        """Query `tool plugins list` and populate the plugins Select."""
        try:
            sel = self.query_one("#plugins-select", Select)
        except Exception:
            return
        out, rc = _run_tool_cmd(["plugins", "list", "--json"])
        opts = []
        names = []
        try:
            if rc == 0 and out:
                names = json.loads(out)
        except Exception:
            names = []
        if not names:
            # fallback to plain list
            out2, rc2 = _run_tool_cmd(["plugins", "list"])
            if rc2 == 0 and out2:
                names = [l.strip() for l in out2.splitlines() if l.strip() and not l.startswith("(")]
        try:
            # Use the Select public API to set options atomically and safely.
            try:
                opts = [(name, name) for name in names]
                # set_options will initialize renderables and select a sensible default
                if hasattr(sel, "set_options"):
                    sel.set_options(opts)
                else:
                    # Fallback to internal assignment when older Textual lacks API
                    try:
                        sel._options = opts
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

        # Populate quick-buttons container
        try:
            btns = self.query_one("#plugins-buttons", Vertical)
            # clear existing
            for c in list(btns.children):
                try:
                    c.remove()
                except Exception:
                    pass
            import re
            self._plugin_name_map.clear()
            for name in names:
                sid = re.sub(r'[^0-9a-zA-Z_]', '_', name)
                btn_id = f"plugin-btn-{sid}"
                try:
                    btns.mount(Button(name, id=btn_id))
                    self._plugin_name_map[sid] = name
                except Exception:
                    pass
        except Exception:
            pass

    # ── Session save on interactive change (highest priority) ─────────────────

    def on_select_changed(self, event: Select.Changed) -> None:
        # Build preset changed -> persist
        if event.select.id == "build-preset" and event.value is not Select.NULL:
            val = str(event.value)
            _out, _rc = _run_tool_cmd(["session", "set", "--key", "last_preset", "--value", val])
            return
        # Plugins selection changed -> show metadata
        if event.select.id == "plugins-select" and event.value is not Select.NULL:
            plugin = str(event.value)
            try:
                out, rc = _run_tool_cmd(["plugins", "describe", plugin])
                if rc == 0 and out:
                    try:
                        meta = json.loads(out)
                        desc = meta.get("description", "")
                        args = meta.get("args", [])
                        # show description and render typed arg widgets
                        try:
                            self.query_one("#plugin-desc", Static).update(desc)
                        except Exception:
                            pass
                        try:
                            self._render_plugin_args(args)
                        except Exception:
                            pass
                    except Exception:
                        try:
                            self.query_one("#plugin-desc", Static).update(out)
                        except Exception:
                            pass
            except Exception:
                pass

    def _format_flag(self, name: str) -> str:
        if not name:
            return name
        if name.startswith("-"):
            return name
        return "--" + name.replace("_", "-")

    def _render_plugin_args(self, args_meta: list) -> None:
        """Render per-argument widgets for the selected plugin.

        When no metadata is provided, a fallback free-text Input is shown.
        """
        try:
            container = self.query_one("#plugin-args-container", Vertical)
        except Exception:
            return
        # clear existing
        for c in list(container.children):
            try:
                c.remove()
            except Exception:
                pass
        self._plugin_arg_map.clear()
        if not args_meta:
            try:
                container.mount(Input(placeholder="args (space-separated)", id="plugin-args-fallback"))
            except Exception:
                pass
            return
        import re
        for a in args_meta:
            if not isinstance(a, dict):
                continue
            name = a.get("name")
            if not name:
                continue
            help_text = a.get("help", "")
            typ = a.get("type", "string")
            default = a.get("default", None)
            sid = re.sub(r'[^0-9a-zA-Z_]', '_', name)
            wid = f"plugin-arg-{sid}"
            self._plugin_arg_map[wid] = {"name": name, "type": typ, "required": bool(a.get("required", False))}
            if typ in ("string", "int"):
                try:
                    container.mount(Label(f"{name} — {help_text}" if help_text else name))
                    inp = Input(placeholder=str(default) if default is not None else "", id=wid)
                    if default is not None:
                        inp.value = str(default)
                    container.mount(inp)
                except Exception:
                    pass
            elif typ in ("bool", "flag"):
                try:
                    cb_label = f"{name} — {help_text}" if help_text else name
                    cb = Checkbox(cb_label, id=wid, value=bool(default) if default is not None else False)
                    container.mount(cb)
                except Exception:
                    # fallback to simple input
                    try:
                        container.mount(Label(f"{name} — {help_text}" if help_text else name))
                        inp = Input(placeholder="true/false" if typ == "bool" else "flag: check to include", id=wid)
                        if default is not None:
                            inp.value = str(default)
                        container.mount(inp)
                    except Exception:
                        pass
            else:
                try:
                    container.mount(Label(f"{name} — {help_text}" if help_text else name))
                    inp = Input(placeholder=str(default) if default is not None else "", id=wid)
                    if default is not None:
                        inp.value = str(default)
                    container.mount(inp)
                except Exception:
                    pass

    def _gather_plugin_args(self, plugin: str) -> list[str]:
        try:
            container = self.query_one("#plugin-args-container", Vertical)
        except Exception:
            return []
        # fallback input handling
        try:
            fb = container.query_one("#plugin-args-fallback", Input)
            # if fallback exists and there are no other arg widgets, use it
            other = [c for c in container.children if getattr(c, "id", None) and c.id != "plugin-args-fallback"]
            if fb is not None and not other:
                txt = fb.value.strip()
                return txt.split() if txt else []
        except Exception:
            pass
        args: list[str] = []
        for child in list(container.children):
            wid = getattr(child, "id", None)
            if not wid or not wid.startswith("plugin-arg-"):
                continue
            meta = self._plugin_arg_map.get(wid, {})
            arg_name = meta.get("name", wid[len("plugin-arg-"):])
            typ = meta.get("type", "string")
            flag = self._format_flag(arg_name)
            try:
                if isinstance(child, Input):
                    val = child.value.strip()
                    if val:
                        args.append(flag)
                        args.append(val)
                elif isinstance(child, Checkbox):
                    checked = bool(child.value)
                    if typ == "flag":
                        if checked:
                            args.append(flag)
                    else:
                        args.append(flag)
                        args.append("true" if checked else "false")
                else:
                    val = getattr(child, "value", None)
                    if val is not None:
                        sval = str(val).strip()
                        if sval:
                            args.append(flag)
                            args.append(sval)
            except Exception:
                pass

        return args

    def _populate_build_presets(self) -> None:
        """Read CMakePresets.json and populate the `build-preset` Select with names.

        Falls back to a small hard-coded list if the file is missing or malformed.
        """
        try:
            sel = self.query_one("#build-preset", Select)
        except Exception:
            return
        presets_file = PROJECT_ROOT / "CMakePresets.json"
        names: list[str] = []
        try:
            if presets_file.exists():
                raw = presets_file.read_text(encoding="utf-8")
                data = json.loads(raw)
                bp = data.get("buildPresets") or []
                if isinstance(bp, list):
                    for entry in bp:
                        if isinstance(entry, dict):
                            nm = entry.get("name")
                            if nm:
                                # Prefer a display label if provided elsewhere
                                label = entry.get("displayName") or nm
                                names.append((label, nm))
        except Exception:
            names = []

        if not names:
            # Fallback options (kept small and sensible)
            fallback = [
                "gcc-debug-static-x86_64",
                "gcc-release-static-x86_64",
                "clang-debug-static-x86_64",
                "clang-release-static-x86_64",
                "msvc-debug-static-x64",
                "msvc-release-static-x64",
            ]
            names = [(n, n) for n in fallback]

        try:
            if hasattr(sel, "set_options"):
                sel.set_options(names)
            else:
                try:
                    sel._options = names
                except Exception:
                    pass
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _preset(self) -> str:
        try:
            v = self.query_one("#build-preset", Select).value
            if v is not Select.NULL:
                return str(v)
        except Exception:
            pass
        return self._initial_preset

    def _show(self, output: str, title: str = "Output") -> None:
        try:
            self.query_one("#result", Static).update(output)
        except Exception:
            pass
        if len(output) > 2000:
            self.push_screen(OutputScreen(title, output))

    # ── Button handlers (all use direct imports) ───────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: C901
        bid    = event.button.id
        preset = self._preset()

        # ── Build tab ─────────────────────────────────────────────────────────
        if bid == "btn-build":
            out, rc = _run_tool_cmd(["build", "build", "--preset", preset])
            self._show(out, "Build")

        elif bid == "btn-check":
            out, rc = _run_tool_cmd(["build", "check", "--preset", preset, "--no-sync"])
            self._show(out, "Check")

        elif bid == "btn-clean":
            out, rc = _run_tool_cmd(["build", "clean"])
            self._show(out, "Clean")

        elif bid == "btn-clean-all":
            out, rc = _run_tool_cmd(["build", "clean", "--all"])
            self._show(out, "Clean All")

        elif bid == "btn-extension":
            out, rc = _run_tool_cmd(["build", "extension"])
            self._show(out, "Extension")

        # ── Libraries — inspect ───────────────────────────────────────────────
        elif bid == "btn-lib-list":
            out, rc = _run_tool_cmd(["lib", "list"])
            self._show(out, "Libraries")
        elif bid == "btn-lib-tree":
            out, rc = _run_tool_cmd(["lib", "tree"])
            self._show(out, "Dep Tree")
        elif bid == "btn-lib-doctor":
            out, rc = _run_tool_cmd(["lib", "doctor"])
            self._show(out, "Doctor")

        # ── Libraries — add ───────────────────────────────────────────────────
        elif bid in ("btn-lib-add", "btn-lib-dry"):
            name = self.query_one("#lib-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name first."); return
            lib_type = self.query_one("#lib-type", Select).value
            tmpl     = self.query_one("#lib-template", Select).value
            deps     = self.query_one("#lib-deps", Input).value.strip()
            dry      = (bid == "btn-lib-dry")
            args = ["lib", "add", name]
            if deps:
                args += ["--deps", deps]
            if tmpl:
                args += ["--template", tmpl]
            if lib_type == "header-only":
                args += ["--header-only"]
            elif lib_type == "interface":
                args += ["--interface"]
            if dry:
                args += ["--dry-run"]
            out, rc = _run_tool_cmd(args)
            self._show(out, f"Add {name}")

        # ── Libraries — remove ────────────────────────────────────────────────
        elif bid in ("btn-lib-remove", "btn-lib-delete"):
            name = self.query_one("#lib-remove-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name first."); return
            args = ["lib", "remove", name]
            if bid == "btn-lib-delete":
                args += ["--delete"]
            out, rc = _run_tool_cmd(args)
            self._show(out, f"Remove {name}")

        # ── Libraries — export ────────────────────────────────────────────────
        elif bid == "btn-lib-export":
            name = self.query_one("#lib-export-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name first."); return
            out, rc = _run_tool_cmd(["lib", "export", name])
            self._show(out, f"Export {name}")

        # ── Project tab ───────────────────────────────────────────────────────
        elif bid == "btn-target-list":
            out, rc = _run_tool_cmd(["sol", "target", "list"])
            self._show(out, "Targets")
        elif bid == "btn-preset-list":
            out, rc = _run_tool_cmd(["sol", "preset", "list"])
            self._show(out, "Presets")
        elif bid == "btn-tc-list":
            out, rc = _run_tool_cmd(["sol", "toolchain", "list"])
            self._show(out, "Toolchains")
        elif bid == "btn-repo-list":
            out, rc = _run_tool_cmd(["sol", "repo", "list"])
            self._show(out, "Repos")
        elif bid == "btn-repo-versions":
            out, rc = _run_tool_cmd(["sol", "repo", "versions"])
            self._show(out, "Versions")
        elif bid == "btn-upgrade-std":
            std = str(self.query_one("#std-select", Select).value)
            out, rc = _run_tool_cmd(["sol", "upgrade-std", "--std", std, "--dry-run"])
            self._show(out, f"Upgrade C++{std}")
        elif bid == "btn-cfg-set":
            key = self.query_one("#cfg-key", Input).value.strip()
            val = self.query_one("#cfg-val", Input).value.strip()
            if not key or not val:
                self._show("⚠ Enter key and value."); return
            out, rc = _run_tool_cmd(["sol", "config", "set", key, val])
            self._show(out, "Config")
        elif bid == "btn-sol-doctor":
            out, rc = _run_tool_cmd(["sol", "doctor"])
            self._show(out, "Doctor")
        elif bid == "btn-ci":
            filt = preset.split("-")[0]
            out, rc = _run_tool_cmd(["sol", "ci", "--preset-filter", filt])
            self._show(out, "CI")

        # ── Info tab ─────────────────────────────────────────────────────────
        elif bid == "btn-info-lib":
            name = self.query_one("#info-lib-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name."); return
            out, rc = _run_tool_cmd(["lib", "info", name])
            self._show(out, f"Info: {name}")

        elif bid == "btn-info-test":
            name = self.query_one("#info-lib-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name."); return
            out, rc = _run_tool_cmd(["lib", "test", name, "--preset", preset])
            self._show(out, f"Test: {name}")

        # ── Plugins tab ─────────────────────────────────────────────────────
        elif bid == "btn-plugin-refresh":
            try:
                self._refresh_plugins()
                self._show("Plugins refreshed", "Plugins")
            except Exception as e:
                self._show(f"Failed to refresh plugins: {e}", "Plugins")

        elif bid == "btn-plugin-run":
            try:
                sel = self.query_one("#plugins-select", Select)
                plugin = sel.value
                if plugin is None or plugin is Select.NULL:
                    self._show("⚠ Select a plugin first.", "Plugins")
                    return
                gathered = self._gather_plugin_args(str(plugin))
                args = [str(plugin)] + gathered
                out, rc = _run_tool_cmd(args)
                self._show(out, f"Plugin: {plugin}")
            except Exception as e:
                self._show(f"Failed to run plugin: {e}", "Plugins")
        elif bid and bid.startswith("plugin-btn-"):
            # Quick-run plugin button pressed
            try:
                sid = bid[len("plugin-btn-"):]
                plugin = self._plugin_name_map.get(sid, sid)
                out, rc = _run_tool_cmd([plugin])
                self._show(out, f"Plugin: {plugin}")
            except Exception as e:
                self._show(f"Failed to run plugin: {e}", "Plugins")

    def action_clear_output(self) -> None:
        try:
            self.query_one("#result", Static).update("")
        except Exception:
            pass


# ── CLI entry point ───────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tui",
        description="Terminal UI (interactive > cli > session > default)",
    )
    parser.add_argument(
        "--preset", default=None,
        help="Initial build preset (overrides session, overridden by interactive selection)",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    initial = _initial_preset(args.preset)
    CppTemplateTUI(initial_preset=initial).run()


if __name__ == "__main__":
    main()
