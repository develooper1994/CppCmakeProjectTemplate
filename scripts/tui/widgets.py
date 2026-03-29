#!/usr/bin/env python3
"""
tui/widgets.py — Small reusable widgets/helpers for the TUI.

Moved from top-level `scripts/tui_widgets.py` into the `scripts.tui`
package. Uses package-relative helpers.
"""
from __future__ import annotations

import re
from typing import List, Tuple, Any

try:
    from textual.widgets import Input, Select, Label, Checkbox, Static, Button
    from textual.containers import Vertical
except Exception:
    # When textual is missing the TUI won't run; propagate a clear error
    raise

from .helpers import read_presets, plugins_list, plugins_describe, run_tool_cmd


def populate_build_presets(select_widget: Select) -> None:
    """Populate a `Select` widget with build presets.

    Keeps the same tolerant code-path as before (supports `set_options`
    or `_options` internal assignment).
    """
    names = read_presets()
    try:
        if hasattr(select_widget, "set_options"):
            select_widget.set_options(names)
        else:
            try:
                select_widget._options = names
            except Exception:
                pass
    except Exception:
        pass


class PluginPanel:
    """Encapsulates plugin UI behaviors used by the main TUI.

    Methods operate on existing `Select` and `Vertical` container
    widgets inside the app rather than creating new ones, so the
    public compose/layout stays unchanged.
    """

    def refresh(self, sel: Select, buttons_container: Vertical, name_map: dict) -> None:
        """Refresh plugin options and buttons.

        * `sel` is the Select widget for plugin names.
        * `buttons_container` is the Vertical container to mount plugin buttons into.
        * `name_map` is mutated to map sanitized ids -> plugin name.
        """
        names = plugins_list()
        try:
            opts = [(name, name) for name in names]
            if hasattr(sel, "set_options"):
                sel.set_options(opts)
            else:
                try:
                    sel._options = opts
                except Exception:
                    pass
        except Exception:
            pass

        # Recreate plugin buttons
        try:
            for c in list(buttons_container.children):
                try:
                    c.remove()
                except Exception:
                    pass
        except Exception:
            pass

        name_map.clear()
        for name in names:
            sid = re.sub(r'[^0-9a-zA-Z_]', '_', name)
            btn_id = f"plugin-btn-{sid}"
            try:
                buttons_container.mount(Button(name, id=btn_id))
                name_map[sid] = name
            except Exception:
                pass

    def render_args(self, container: Vertical, args_meta: List[dict], arg_map: dict) -> None:
        """Render plugin argument inputs into `container` and populate `arg_map`.

        This mirrors the original `_render_plugin_args` logic from `tui_ui.py`.
        """
        try:
            for c in list(container.children):
                try:
                    c.remove()
                except Exception:
                    pass
        except Exception:
            pass

        arg_map.clear()
        if not args_meta:
            try:
                container.mount(Input(placeholder="args (space-separated)", id="plugin-args-fallback"))
            except Exception:
                pass
            return

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
            arg_map[wid] = {"name": name, "type": typ, "required": bool(a.get("required", False))}
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

    def gather_args(self, container: Vertical, arg_map: dict) -> List[str]:
        """Collect arguments from the plugin args container using `arg_map` metadata."""
        try:
            fb = None
            try:
                fb = container.query_one("#plugin-args-fallback", Input)
            except Exception:
                fb = None
            other = [c for c in container.children if getattr(c, "id", None) and c.id != "plugin-args-fallback"]
            if fb is not None and not other:
                txt = fb.value.strip()
                return txt.split() if txt else []
        except Exception:
            pass

        args: List[str] = []
        for child in list(container.children):
            wid = getattr(child, "id", None)
            if not wid or not wid.startswith("plugin-arg-"):
                continue
            meta = arg_map.get(wid, {})
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

    @staticmethod
    def _format_flag(name: str) -> str:
        if not name:
            return name
        if name.startswith("-"):
            return name
        return "--" + name.replace("_", "-")


class LibraryPanel:
    """Helpers for the Library tab operations.

    Methods accept the `app` instance and operate on known widget ids so
    the main `CppTemplateTUI` can delegate behavior while keeping layout
    intact.
    """

    def list(self) -> tuple[str, int]:
        return run_tool_cmd(["lib", "list"])

    def tree(self) -> tuple[str, int]:
        return run_tool_cmd(["lib", "tree"])

    def doctor(self) -> tuple[str, int]:
        return run_tool_cmd(["lib", "doctor"])

    def add(self, app, dry: bool = False) -> tuple[str, int]:
        try:
            name = app.query_one("#lib-name").value.strip()
        except Exception:
            return ("", 1)
        if not name:
            return ("⚠ Enter a library name first.", 2)
        try:
            lib_type = app.query_one("#lib-type").value
        except Exception:
            lib_type = ""
        try:
            tmpl = app.query_one("#lib-template").value
        except Exception:
            tmpl = ""
        try:
            deps = app.query_one("#lib-deps").value.strip()
        except Exception:
            deps = ""

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
        return run_tool_cmd(args)

    def remove(self, app, delete: bool = False) -> tuple[str, int]:
        try:
            name = app.query_one("#lib-remove-name").value.strip()
        except Exception:
            return ("", 1)
        if not name:
            return ("⚠ Enter a library name first.", 2)
        args = ["lib", "remove", name]
        if delete:
            args += ["--delete"]
        return run_tool_cmd(args)

    def export(self, app) -> tuple[str, int]:
        try:
            name = app.query_one("#lib-export-name").value.strip()
        except Exception:
            return ("", 1)
        if not name:
            return ("⚠ Enter a library name.", 2)
        return run_tool_cmd(["lib", "export", name])


class ProjectPanel:
    """Helpers for the Project tab operations (sol.* commands)."""

    def target_list(self) -> tuple[str, int]:
        return run_tool_cmd(["sol", "target", "list"])

    def preset_list(self) -> tuple[str, int]:
        return run_tool_cmd(["sol", "preset", "list"])

    def toolchain_list(self) -> tuple[str, int]:
        return run_tool_cmd(["sol", "toolchain", "list"])

    def repo_list(self) -> tuple[str, int]:
        return run_tool_cmd(["sol", "repo", "list"])

    def repo_versions(self) -> tuple[str, int]:
        return run_tool_cmd(["sol", "repo", "versions"])

    def upgrade_std(self, app) -> tuple[str, int]:
        try:
            std = str(app.query_one("#std-select").value)
        except Exception:
            return ("", 1)
        return run_tool_cmd(["sol", "upgrade-std", "--std", std, "--dry-run"])

    def cfg_set(self, app) -> tuple[str, int]:
        try:
            key = app.query_one("#cfg-key").value.strip()
            val = app.query_one("#cfg-val").value.strip()
        except Exception:
            return ("", 1)
        if not key or not val:
            return ("⚠ Enter key and value.", 2)
        return run_tool_cmd(["sol", "config", "set", key, val])

    def sol_doctor(self) -> tuple[str, int]:
        return run_tool_cmd(["sol", "doctor"])

    def ci(self, preset: str) -> tuple[str, int]:
        filt = preset.split("-")[0] if preset else ""
        return run_tool_cmd(["sol", "ci", "--preset-filter", filt])


class InfoPanel:
    """Helpers for the Info tab operations."""

    def info_lib(self, app) -> tuple[str, int]:
        try:
            name = app.query_one("#info-lib-name").value.strip()
        except Exception:
            return ("", 1)
        if not name:
            return ("⚠ Enter a library name.", 2)
        return run_tool_cmd(["lib", "info", name])

    def run_tests(self, app, preset: str) -> tuple[str, int]:
        try:
            name = app.query_one("#info-lib-name").value.strip()
        except Exception:
            return ("", 1)
        if not name:
            return ("⚠ Enter a library name.", 2)
        return run_tool_cmd(["lib", "test", name, "--preset", preset])
