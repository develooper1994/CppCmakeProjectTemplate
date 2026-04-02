"""
core/generator/presets.py — CMakePresets.json generator component
=================================================================

Wraps the existing ``core.commands.presets`` logic so that
``tool generate`` also produces ``CMakePresets.json`` from
``tool.toml [presets]``.
"""
from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from core.generator.engine import ProjectContext

# Re-use all preset-building helpers from the CLI command module.
from core.commands.presets import (
    _base_presets,
    _concrete_configure_presets,
    _build_presets,
    _test_presets,
)


def _presets_config_from_ctx(ctx: "ProjectContext") -> dict[str, Any]:
    """Translate ``ctx.presets`` into the dict expected by preset helpers."""
    raw = dict(ctx.presets) if ctx.presets else {}
    defaults: dict[str, Any] = {
        "compilers":           ["gcc", "clang"],
        "build_types":         ["debug", "release", "relwithdebinfo"],
        "linkages":            ["static", "dynamic"],
        "arches":              ["x86_64"],
        "allocators":          ["default"],
        "cmake_minimum_major": 3,
        "cmake_minimum_minor": 25,
        "default_preset":      "gcc-debug-static-x86_64",
        "cuda_architectures":  "native",
        "generator":           "Ninja",
        "skip_combinations":   [],
    }
    defaults.update(raw)
    return defaults


def generate_all(ctx: "ProjectContext", target_dir: "Path") -> dict[str, str]:
    """Return ``{"CMakePresets.json": <content>}``."""
    cfg = _presets_config_from_ctx(ctx)

    base_cfg = _base_presets(cfg)
    concrete = _concrete_configure_presets(cfg)
    all_cfg  = base_cfg + concrete
    all_names = [p["name"] for p in concrete]

    builds = _build_presets(all_names)
    tests  = _test_presets(all_names)

    maj  = int(cfg.get("cmake_minimum_major", 3))
    min_ = int(cfg.get("cmake_minimum_minor", 25))

    document: dict[str, Any] = {
        "version": 4,
        "cmakeMinimumRequired": {"major": maj, "minor": min_, "patch": 0},
        "vendor": {
            "tool-presets-generator": {
                "note": (
                    "AUTO-GENERATED — DO NOT EDIT MANUALLY. "
                    "Edit tool.toml [presets] and re-run `tool generate`."
                ),
            }
        },
        "configurePresets": all_cfg,
        "buildPresets": builds,
        "testPresets": tests,
    }

    return {"CMakePresets.json": json.dumps(document, indent=2) + "\n"}
