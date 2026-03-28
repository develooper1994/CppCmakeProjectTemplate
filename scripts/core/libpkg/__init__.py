"""Library packaging helpers (modularized from toollib).

Public surface:
- create_library
- validate_name
- paths_for

Keep this module small: implementation details live in submodules.
"""

from .create import create_library
from .paths import validate_name, paths_for

__all__ = ["create_library", "validate_name", "paths_for"]
"""core.libpkg — library scaffolding package

Provides a compact, modular implementation for library scaffolding.
"""
from .create import create_library
from .paths import validate_name, paths_for, LibPaths
from .templates import (
    lib_header, lib_source, lib_header_singleton, lib_source_singleton,
    lib_header_pimpl, lib_source_pimpl, lib_header_factory, lib_source_factory,
    lib_header_observer, lib_source_observer, lib_cmakelists, lib_cmakelists_header_only,
)
from .tokens import contains_token, replace_token

__all__ = [
    "create_library",
    "validate_name", "paths_for", "LibPaths",
    "lib_header", "lib_source", "lib_header_singleton", "lib_source_singleton",
    "lib_header_pimpl", "lib_source_pimpl", "lib_header_factory", "lib_source_factory",
    "lib_header_observer", "lib_source_observer", "lib_cmakelists", "lib_cmakelists_header_only",
    "contains_token", "replace_token",
]
