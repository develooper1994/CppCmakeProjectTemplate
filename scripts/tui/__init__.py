"""Lazy facade for the `scripts.tui` package.

Expose key symbols lazily so importing the package doesn't pull in the
heavy `textual` dependency at import-time. Attributes are resolved on
first access and cached on the package module.
"""
from __future__ import annotations

import importlib
from typing import Any


_MAPPING: dict[str, tuple[str, str]] = {
    "CppTemplateTUI": ("scripts.tui.ui", "CppTemplateTUI"),
    "OutputScreen": ("scripts.tui.screens", "OutputScreen"),
    "run_tool_cmd": ("scripts.tui.helpers", "run_tool_cmd"),
    "read_presets": ("scripts.tui.helpers", "read_presets"),
    "initial_preset": ("scripts.tui.helpers", "initial_preset"),
    "DEFAULT_PRESET": ("scripts.tui.helpers", "DEFAULT_PRESET"),
    "populate_build_presets": ("scripts.tui.widgets", "populate_build_presets"),
    "PluginPanel": ("scripts.tui.widgets", "PluginPanel"),
    "LibraryPanel": ("scripts.tui.widgets", "LibraryPanel"),
    "ProjectPanel": ("scripts.tui.widgets", "ProjectPanel"),
    "InfoPanel": ("scripts.tui.widgets", "InfoPanel"),
}


def _import_attr(module_name: str, attr: str):
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        # Fallback to legacy top-level `tui.*` modules
        bare = module_name.replace("scripts.", "")
        mod = importlib.import_module(bare)
    return getattr(mod, attr)


def __getattr__(name: str) -> Any:
    if name in _MAPPING:
        module_name, attr = _MAPPING[name]
        val = _import_attr(module_name, attr)
        globals()[name] = val
        return val
    raise AttributeError(name)


def __dir__() -> list[str]:
    keys = list(_MAPPING.keys())
    return keys


__all__ = list(_MAPPING.keys())
