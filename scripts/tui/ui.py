"""tui.ui — UI components for the TUI (widgets, screens, app class).

Moved from top-level `scripts/tui_ui.py` into the `scripts.tui` package.
"""
from __future__ import annotations

import sys
import re

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, ScrollableContainer
    from textual.widgets import (
        Button, Footer, Header, Input, Label,
        Select, Static, TabbedContent, TabPane, Checkbox,
    )
except ImportError:
    print("Textual not installed. Run: pip3 install textual --break-system-packages")
    sys.exit(1)

# Package-local imports (prefer relative imports to avoid circular fallbacks)
from .helpers import run_tool_cmd, read_presets, plugins_list, plugins_describe, DEFAULT_PRESET
from .widgets import PluginPanel, LibraryPanel, ProjectPanel, InfoPanel
from .screens import OutputScreen


def _run_tool_cmd(args_list: list[str]) -> tuple[str, int]:
    return run_tool_cmd(args_list)


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
    # Optional panel widgets — may be None when textual isn't available or
    # in environments where panels cannot be constructed during import.
    _plugin_panel: PluginPanel | None
    _library_panel: LibraryPanel | None
    _project_panel: ProjectPanel | None
    _info_panel: InfoPanel | None

    def __init__(self, initial_preset: str = DEFAULT_PRESET) -> None:
        super().__init__()
        self._initial_preset = initial_preset
        self._plugin_name_map: dict[str, str] = {}
        # mapping widget id -> arg meta (name, type, required)
        self._plugin_arg_map: dict[str, dict] = {}
        # encapsulated plugin panel behavior
        try:
            self._plugin_panel = PluginPanel()
        except Exception:
            self._plugin_panel = None
        try:
            self._library_panel = LibraryPanel()
        except Exception:
            self._library_panel = None
        try:
            self._project_panel = ProjectPanel()
        except Exception:
            self._project_panel = None
        try:
            self._info_panel = InfoPanel()
        except Exception:
            self._info_panel = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():

            # Build tab
            with TabPane("🔨 Build", id="tab-build"):
                with Vertical(id="main"):
                    yield Label("Build Operations", classes="section-title")
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
                            options=[("Normal","normal"),("Header-only","header-only"),("Interface","interface")],
                            allow_blank=False, id="lib-type",
                        )
                        yield Select(
                            options=[("No template",""),("Singleton","singleton"),("Pimpl","pimpl"),("Observer","observer"),("Factory","factory")],
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
                            options=[("C++14","14"),("C++17","17"),("C++20","20"),("C++23","23")],
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

    def on_mount(self) -> None:
        try:
            try:
                self._populate_build_presets()
            except Exception:
                pass
            sel = self.query_one("#build-preset", Select)
            try:
                opts = getattr(sel, "options", None) or getattr(sel, "_options", None) or []
                valid = [v for _, v in opts]
                if self._initial_preset in valid:
                    try:
                        sel.value = self._initial_preset
                    except Exception:
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
        try:
            self._refresh_plugins()
        except Exception:
            pass

    def _refresh_plugins(self) -> None:
        try:
            sel = self.query_one("#plugins-select", Select)
        except Exception:
            return
        try:
            btns = self.query_one("#plugins-buttons", Vertical)
        except Exception:
            btns = None

        try:
            if self._plugin_panel:
                self._plugin_panel.refresh(sel, btns, self._plugin_name_map)
            else:
                # fallback to previous inline behavior
                names = plugins_list()
                opts = [(name, name) for name in names]
                try:
                    if hasattr(sel, "set_options"):
                        sel.set_options(opts)
                    else:
                        sel._options = opts
                except Exception:
                    pass
                try:
                    if btns is not None:
                        for c in list(btns.children):
                            try:
                                c.remove()
                            except Exception:
                                pass
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
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "build-preset" and event.value is not Select.NULL:
            val = str(event.value)
            _out, _rc = _run_tool_cmd(["session", "set", "--key", "last_preset", "--value", val])
            return
        if event.select.id == "plugins-select" and event.value is not Select.NULL:
            plugin = str(event.value)
            try:
                meta, out, rc = plugins_describe(plugin)
                if rc == 0 and out:
                    try:
                        desc = meta.get("description", "") if isinstance(meta, dict) else ""
                        args = meta.get("args", []) if isinstance(meta, dict) else []
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
        try:
            container = self.query_one("#plugin-args-container", Vertical)
        except Exception:
            return
        try:
            if self._plugin_panel:
                self._plugin_panel.render_args(container, args_meta or [], self._plugin_arg_map)
                return
        except Exception:
            pass
        # fallback: keep inline behavior if plugin_panel not available
        try:
            for c in list(container.children):
                try:
                    c.remove()
                except Exception:
                    pass
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
        try:
            if self._plugin_panel:
                return self._plugin_panel.gather_args(container, self._plugin_arg_map)
        except Exception:
            pass
        try:
            fb = container.query_one("#plugin-args-fallback", Input)
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
        try:
            sel = self.query_one("#build-preset", Select)
        except Exception:
            return
        names = read_presets()
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

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: C901
        bid    = event.button.id
        preset = self._preset()

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

        elif bid == "btn-lib-list":
            try:
                if self._library_panel:
                    out, rc = self._library_panel.list()
                else:
                    out, rc = _run_tool_cmd(["lib", "list"])
                self._show(out, "Libraries")
            except Exception as e:
                self._show(f"Failed to list libraries: {e}", "Libraries")

        elif bid == "btn-lib-tree":
            try:
                if self._library_panel:
                    out, rc = self._library_panel.tree()
                else:
                    out, rc = _run_tool_cmd(["lib", "tree"])
                self._show(out, "Dep Tree")
            except Exception as e:
                self._show(f"Failed to show dep tree: {e}", "Dep Tree")

        elif bid == "btn-lib-doctor":
            try:
                if self._library_panel:
                    out, rc = self._library_panel.doctor()
                else:
                    out, rc = _run_tool_cmd(["lib", "doctor"])
                self._show(out, "Doctor")
            except Exception as e:
                self._show(f"Failed to run doctor: {e}", "Doctor")

        elif bid in ("btn-lib-add", "btn-lib-dry"):
            dry = (bid == "btn-lib-dry")
            try:
                if self._library_panel:
                    out, rc = self._library_panel.add(self, dry=dry)
                    try:
                        name = self.query_one("#lib-name", Input).value.strip()
                    except Exception:
                        name = ""
                else:
                    name = self.query_one("#lib-name", Input).value.strip()
                    if not name:
                        self._show("⚠ Enter a library name first.")
                        return
                    lib_type = self.query_one("#lib-type", Select).value
                    tmpl     = self.query_one("#lib-template", Select).value
                    deps     = self.query_one("#lib-deps", Input).value.strip()
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
            except Exception as e:
                self._show(f"Failed to add library: {e}", "Libraries")

        elif bid in ("btn-lib-remove", "btn-lib-delete"):
            delete = (bid == "btn-lib-delete")
            try:
                if self._library_panel:
                    out, rc = self._library_panel.remove(self, delete=delete)
                    try:
                        name = self.query_one("#lib-remove-name", Input).value.strip()
                    except Exception:
                        name = ""
                else:
                    name = self.query_one("#lib-remove-name", Input).value.strip()
                    if not name:
                        self._show("⚠ Enter a library name first.")
                        return
                    args = ["lib", "remove", name]
                    if delete:
                        args += ["--delete"]
                    out, rc = _run_tool_cmd(args)
                self._show(out, f"Remove {name}")
            except Exception as e:
                self._show(f"Failed to remove library: {e}", "Libraries")

        elif bid == "btn-lib-export":
            try:
                if self._library_panel:
                    out, rc = self._library_panel.export(self)
                    try:
                        name = self.query_one("#lib-export-name", Input).value.strip()
                    except Exception:
                        name = ""
                else:
                    name = self.query_one("#lib-export-name", Input).value.strip()
                    if not name:
                        self._show("⚠ Enter a library name.")
                        return
                    out, rc = _run_tool_cmd(["lib", "export", name])
                self._show(out, f"Export {name}")
            except Exception as e:
                self._show(f"Failed to export library: {e}", "Libraries")

        elif bid == "btn-target-list":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.target_list()
                else:
                    out, rc = _run_tool_cmd(["sol", "target", "list"])
                self._show(out, "Targets")
            except Exception as e:
                self._show(f"Failed to list targets: {e}", "Targets")

        elif bid == "btn-preset-list":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.preset_list()
                else:
                    out, rc = _run_tool_cmd(["sol", "preset", "list"])
                self._show(out, "Presets")
            except Exception as e:
                self._show(f"Failed to list presets: {e}", "Presets")

        elif bid == "btn-tc-list":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.toolchain_list()
                else:
                    out, rc = _run_tool_cmd(["sol", "toolchain", "list"])
                self._show(out, "Toolchains")
            except Exception as e:
                self._show(f"Failed to list toolchains: {e}", "Toolchains")

        elif bid == "btn-repo-list":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.repo_list()
                else:
                    out, rc = _run_tool_cmd(["sol", "repo", "list"])
                self._show(out, "Repos")
            except Exception as e:
                self._show(f"Failed to list repos: {e}", "Repos")

        elif bid == "btn-repo-versions":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.repo_versions()
                else:
                    out, rc = _run_tool_cmd(["sol", "repo", "versions"])
                self._show(out, "Versions")
            except Exception as e:
                self._show(f"Failed to get repo versions: {e}", "Versions")

        elif bid == "btn-upgrade-std":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.upgrade_std(self)
                else:
                    std = str(self.query_one("#std-select", Select).value)
                    out, rc = _run_tool_cmd(["sol", "upgrade-std", "--std", std, "--dry-run"])
                try:
                    std = str(self.query_one("#std-select", Select).value)
                except Exception:
                    std = ""
                self._show(out, f"Upgrade C++{std}")
            except Exception as e:
                self._show(f"Failed to upgrade std: {e}", "Project")

        elif bid == "btn-cfg-set":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.cfg_set(self)
                else:
                    key = self.query_one("#cfg-key", Input).value.strip()
                    val = self.query_one("#cfg-val", Input).value.strip()
                    if not key or not val:
                        self._show("⚠ Enter key and value.")
                        return
                    out, rc = _run_tool_cmd(["sol", "config", "set", key, val])
                self._show(out, "Config")
            except Exception as e:
                self._show(f"Failed to set config: {e}", "Project")

        elif bid == "btn-sol-doctor":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.sol_doctor()
                else:
                    out, rc = _run_tool_cmd(["sol", "doctor"])
                self._show(out, "Doctor")
            except Exception as e:
                self._show(f"Failed to run sol doctor: {e}", "Project")

        elif bid == "btn-ci":
            try:
                if self._project_panel:
                    out, rc = self._project_panel.ci(preset)
                else:
                    filt = preset.split("-")[0]
                    out, rc = _run_tool_cmd(["sol", "ci", "--preset-filter", filt])
                self._show(out, "CI")
            except Exception as e:
                self._show(f"Failed to run CI: {e}", "Project")

        elif bid == "btn-info-lib":
            try:
                if self._info_panel:
                    out, rc = self._info_panel.info_lib(self)
                    try:
                        name = self.query_one("#info-lib-name", Input).value.strip()
                    except Exception:
                        name = ""
                else:
                    name = self.query_one("#info-lib-name", Input).value.strip()
                    if not name:
                        self._show("⚠ Enter a library name.")
                        return
                    out, rc = _run_tool_cmd(["lib", "info", name])
                self._show(out, f"Info: {name}")
            except Exception as e:
                self._show(f"Failed to get library info: {e}", "Info")

        elif bid == "btn-info-test":
            try:
                if self._info_panel:
                    out, rc = self._info_panel.run_tests(self, preset)
                    try:
                        name = self.query_one("#info-lib-name", Input).value.strip()
                    except Exception:
                        name = ""
                else:
                    name = self.query_one("#info-lib-name", Input).value.strip()
                    if not name:
                        self._show("⚠ Enter a library name.")
                        return
                    out, rc = _run_tool_cmd(["lib", "test", name, "--preset", preset])
                self._show(out, f"Test: {name}")
            except Exception as e:
                self._show(f"Failed to run tests: {e}", "Info")

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
