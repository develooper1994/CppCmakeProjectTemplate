from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VALID_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(slots=True)
class LibPaths:
    lib_dir: Path
    include_dir: Path
    include_subdir: Path
    header_file: Path
    src_dir: Path
    source_file: Path
    cmake: Path
    readme: Path
    tests_dir: Path


def validate_name(name: str) -> None:
    if not VALID_NAME_RE.match(name):
        raise ValueError("Invalid library name: %r" % name)


def paths_for(name: str, root: Optional[Path] = None) -> LibPaths:
    root = Path(root) if root is not None else Path(__file__).resolve().parents[4]
    lib_dir = root / "libs" / name
    include_dir = lib_dir / "include"
    include_subdir = include_dir / name
    header_file = include_subdir / f"{name}.h"
    src_dir = lib_dir / "src"
    source_file = src_dir / f"{name}.cpp"
    cmake = lib_dir / "CMakeLists.txt"
    readme = lib_dir / "README.md"
    tests_dir = root / "tests" / "unit" / name
    return LibPaths(lib_dir, include_dir, include_subdir, header_file, src_dir, source_file, cmake, readme, tests_dir)

