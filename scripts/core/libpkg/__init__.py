"""core.libpkg — library scaffolding package.

Public API:
- create_library
- validate_name
- paths_for
- LibPaths
- Template/snippet helpers and token utilities

This module keeps a small public surface while implementations live in
submodules under `scripts/core/libpkg`.
"""

from .create import create_library, remove_library, rename_library, move_library
from .paths import validate_name, paths_for, LibPaths
from .templates import (
    lib_header, lib_source, lib_header_singleton, lib_source_singleton,
    lib_header_pimpl, lib_source_pimpl, lib_header_factory, lib_source_factory,
    lib_header_observer, lib_source_observer, lib_cmakelists, lib_cmakelists_header_only,
)
from .tokens import contains_token, replace_token, apply_template_dir

__all__ = [
    "create_library", "remove_library", "rename_library", "move_library",
    "validate_name", "paths_for", "LibPaths",
    "lib_header", "lib_source", "lib_header_singleton", "lib_source_singleton",
    "lib_header_pimpl", "lib_source_pimpl", "lib_header_factory", "lib_source_factory",
    "lib_header_observer", "lib_source_observer", "lib_cmakelists", "lib_cmakelists_header_only",
    "contains_token", "replace_token", "apply_template_dir",
]
