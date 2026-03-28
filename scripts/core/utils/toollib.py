#!/usr/bin/env python3
"""Compatibility shim — re-export the new modular libpkg API.

This file exists so older importers that used `core.utils.toollib`
keep working while the implementation is split into `core.libpkg`.
"""

from core.libpkg import create_library, validate_name, paths_for  # re-export

__all__ = ["create_library", "validate_name", "paths_for"]
