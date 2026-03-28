from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .paths import paths_for, validate_name
from .templates import (
    lib_cmakelists,
    lib_cmakelists_header_only,
    lib_header,
    lib_source,
    lib_header_singleton,
    lib_source_singleton,
    lib_header_pimpl,
    lib_source_pimpl,
    lib_header_factory,
    lib_source_factory,
    lib_header_observer,
    lib_source_observer,
)
from .tokens import apply_template_dir
import shutil
from datetime import datetime


def create_library(
    name: str,
    version: str = "1.0.0",
    namespace: Optional[str] = None,
    deps: Optional[List[str]] = None,
    header_only: bool = False,
    interface: bool = False,
    template: str = "",
    cxx_standard: str = "",
    link_app: bool = False,
    dry_run: bool = False,
    root: Optional[Path] = None,
) -> None:
    # Debug: write a marker to build_logs to trace invocation and parameters
    try:
        project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]
        log_dir = project_root / "build_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "lib_create_debug.log", "a", encoding="utf-8") as _f:
            _f.write(f"{datetime.now().isoformat()} create_library called name={name} template={template} dry_run={dry_run} root={root}\n")
    except Exception:
        pass

    deps = deps or []
    validate_name(name)
    p = paths_for(name, root)
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]

    # If a template directory exists under extension/templates/libs/<template>, apply it.
    if template:
        template_dir = project_root / "extension" / "templates" / "libs" / template
        if template_dir.exists() and template_dir.is_dir():
            if dry_run:
                print("Dry-run: would create from template:", template_dir)
                apply_template_dir(template_dir, p.lib_dir, name, dry_run=True)
                return
            # create and populate from template
            apply_template_dir(template_dir, p.lib_dir, name, dry_run=False)
            print("Created library from template", template)
            # register in libs/CMakeLists if requested
            if link_app:
                libs_cmake = project_root / "libs" / "CMakeLists.txt"
                entry = f"add_subdirectory({name})\n"
                if dry_run:
                    print("Dry-run: would update:", libs_cmake)
                else:
                    if libs_cmake.exists():
                        txt = libs_cmake.read_text(encoding="utf-8")
                        if f"add_subdirectory({name})" not in txt:
                            libs_cmake.write_text(txt.rstrip() + "\n" + entry, encoding="utf-8")
                    else:
                        libs_cmake.parent.mkdir(parents=True, exist_ok=True)
                        libs_cmake.write_text(entry, encoding="utf-8")
                    print("Registered library in libs/CMakeLists.txt")
            return

    if p.lib_dir.exists():
        raise FileExistsError(name)

    if dry_run:
        print("Dry-run: would create:")
        print("  ", p.lib_dir)
        return

    p.lib_dir.mkdir(parents=True, exist_ok=False)
    p.include_subdir.mkdir(parents=True)
    p.src_dir.mkdir(parents=True)

    if header_only or interface:
        p.header_file.write_text(lib_header(name, namespace), encoding="utf-8")
        p.cmake.write_text(lib_cmakelists_header_only(name, version, namespace, deps, cxx_standard), encoding="utf-8")
    else:
        if template == "singleton":
            p.header_file.write_text(lib_header_singleton(name, namespace), encoding="utf-8")
            p.source_file.write_text(lib_source_singleton(name, namespace), encoding="utf-8")
        elif template == "pimpl":
            p.header_file.write_text(lib_header_pimpl(name, namespace), encoding="utf-8")
            p.source_file.write_text(lib_source_pimpl(name, namespace), encoding="utf-8")
        elif template == "factory":
            p.header_file.write_text(lib_header_factory(name, namespace), encoding="utf-8")
            p.source_file.write_text(lib_source_factory(name, namespace), encoding="utf-8")
        elif template == "observer":
            p.header_file.write_text(lib_header_observer(name, namespace), encoding="utf-8")
            p.source_file.write_text(lib_source_observer(name, namespace), encoding="utf-8")
        else:
            p.header_file.write_text(lib_header(name, namespace), encoding="utf-8")
            p.source_file.write_text(lib_source(name, namespace), encoding="utf-8")
        p.cmake.write_text(lib_cmakelists(name, version, namespace, deps, cxx_standard), encoding="utf-8")

    p.readme.write_text(f"# {name}\n\nGenerated library {name}\n", encoding="utf-8")

    p.tests_dir.mkdir(parents=True, exist_ok=True)
    (p.tests_dir / f"{name}_test.cpp").write_text(
        "#include <gtest/gtest.h>\n\nTEST(Stub, AlwaysPass) { EXPECT_TRUE(true); }\n", encoding="utf-8"
    )

    print("Created library", name)

    # Optionally register the library in root libs/CMakeLists.txt
    if link_app:
        libs_cmake = project_root / "libs" / "CMakeLists.txt"
        entry = f"add_subdirectory({name})\n"
        if dry_run:
            print("Dry-run: would update:", libs_cmake)
        else:
            if libs_cmake.exists():
                txt = libs_cmake.read_text(encoding="utf-8")
                if f"add_subdirectory({name})" not in txt:
                    libs_cmake.write_text(txt.rstrip() + "\n" + entry, encoding="utf-8")
            else:
                libs_cmake.parent.mkdir(parents=True, exist_ok=True)
                libs_cmake.write_text(entry, encoding="utf-8")
            print("Registered library in libs/CMakeLists.txt")

