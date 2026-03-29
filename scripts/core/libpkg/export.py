from __future__ import annotations

from pathlib import Path
from typing import Optional

from .paths import paths_for

try:
    from .jinja_helpers import render_template_file as _render_template_file
    _USE_JINJA_EXPORT = True
except Exception:
    _render_template_file = None
    _USE_JINJA_EXPORT = False


def create_export_snippet(name: str, root: Optional[Path] = None, dry_run: bool = False) -> Path:
    """Create install/export helper files for a library.

    Writes:
    - libs/<name>/install.cmake  (calls install_project_library)
    - libs/<name>/cmake/<name>Config.cmake.in  (copied from project template)

    Returns the path to the install.cmake file (or the expected path in dry-run).
    """
    p = paths_for(name, root)
    if not p.lib_dir.exists():
        raise FileNotFoundError(name)

    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]

    cmake_dir = p.lib_dir / "cmake"
    cmake_dir.mkdir(parents=True, exist_ok=True)

    # Copy the generic LibraryConfig.cmake.in into the library folder if it doesn't exist
    src_template = project_root / "cmake" / "LibraryConfig.cmake.in"
    dest_template = cmake_dir / f"{name}Config.cmake.in"
    if src_template.exists() and not dest_template.exists():
        if dry_run:
            print("Dry-run: would copy:", src_template, "->", dest_template)
        else:
            dest_template.write_text(src_template.read_text(encoding="utf-8"), encoding="utf-8")

    install_file = p.lib_dir / "install.cmake"
    if _USE_JINJA_EXPORT:
        content = _render_template_file("export_install.jinja2", name=name)
    else:
        content = (
            f"# Auto-generated install/export for {name}\n"
            "include(\"${PROJECT_SOURCE_DIR}/cmake/ProjectExport.cmake\")\n\n"
            f"install_project_library({name} {name})\n"
        )

    if dry_run:
        print("Dry-run: would create:", install_file)
        print("---\n" + content)
        return install_file

    install_file.write_text(content, encoding="utf-8")
    return install_file
