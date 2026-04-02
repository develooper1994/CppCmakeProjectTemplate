"""Library management command implementations and CLIResult wrappers."""
from __future__ import annotations

import re
import sys

from core.utils.common import CLIResult, run_proc, PROJECT_ROOT, GlobalConfig
from core.utils.command_utils import wrap_command
from core.libpkg import (
    create_library,
    remove_library,
    rename_library,
    move_library,
)
from core.libpkg.jinja_helpers import (
    render_template_file as _render_template_file,
    JINJA_AVAILABLE as _USE_JINJA_LIBCMD,
)
from ._helpers import LIBS_DIR, _ensure_libs, _get_lib_deps


# ── Implementation functions ──────────────────────────────────────────────────

def _impl_cmd_list(args) -> None:
    _ensure_libs()
    for d in sorted([p.name for p in LIBS_DIR.iterdir() if p.is_dir()]):
        deps = _get_lib_deps(d)
        dep_str = f" -> ({', '.join(deps)})" if deps else ""
        print(f"{d}{dep_str}")


def _impl_cmd_tree(args) -> None:
    _ensure_libs()
    libs = sorted([p.name for p in LIBS_DIR.iterdir() if p.is_dir()])

    def print_deps(name: str, visited: set[str], indent: int = 0):
        if name in visited:
            print("  " * indent + f"└─ {name} (circular!)")
            return
        visited.add(name)
        deps = _get_lib_deps(name)
        prefix = "  " * indent + ("└─ " if indent > 0 else "")
        print(f"{prefix}{name}")
        for d in deps:
            if (LIBS_DIR / d).exists():
                print_deps(d, visited.copy(), indent + 1)
            else:
                print("  " * (indent + 1) + f"└─ {d} (external)")

    for lib in libs:
        is_root = True
        for other in libs:
            if lib in _get_lib_deps(other):
                is_root = False
                break
        if is_root:
            print_deps(lib, set())


def _impl_cmd_doctor(args) -> None:
    _ensure_libs()
    problems = 0

    for d in LIBS_DIR.iterdir():
        if d.is_dir():
            name = d.name
            cm = d / "CMakeLists.txt"
            if not cm.exists():
                print(f"❌ {name}: Missing CMakeLists.txt")
                problems += 1
            inc = d / "include" / name
            if not inc.exists() and not (d / "include").exists():
                content = cm.read_text(encoding="utf-8") if cm.exists() else ""
                if "INTERFACE" not in content:
                    print(f"⚠️ {name}: Missing standard include structure")

            deps = _get_lib_deps(name)
            for dep in deps:
                if "::" not in dep and not (LIBS_DIR / dep).exists() and dep not in ("GTest::gtest_main", "GTest::gtest"):
                    print(f"⚠️ {name}: Depends on '{dep}' which is not in libs/ and not namespaced")

    libs_cm = PROJECT_ROOT / "libs" / "CMakeLists.txt"
    if libs_cm.exists():
        content = libs_cm.read_text(encoding="utf-8")
        matches = re.findall(r'add_subdirectory\(\s*([^)]+)\s*\)', content)
        for sub in matches:
            sub = sub.strip()
            if not (PROJECT_ROOT / "libs" / sub).exists():
                print(f"❌ Orphaned entry in libs/CMakeLists.txt: add_subdirectory({sub})")
                problems += 1

    tests_cm = PROJECT_ROOT / "tests" / "unit" / "CMakeLists.txt"
    if tests_cm.exists():
        content = tests_cm.read_text(encoding="utf-8")
        matches = re.findall(r'add_subdirectory\(\s*([^)]+)\s*\)', content)
        for sub in matches:
            sub = sub.strip()
            if not (PROJECT_ROOT / "libs" / sub).exists():
                print(f"❌ Orphaned entry in tests/unit/CMakeLists.txt: add_subdirectory({sub})")
                problems += 1

    if problems == 0:
        print("✅ toollib doctor: All libraries look healthy")
    else:
        print(f"\nFound {problems} problems. Use 'tool lib remove <name>' to detach orphaned entries.")


def _impl_cmd_add(args) -> None:
    _ensure_libs()
    name = args.name
    deps = []
    if getattr(args, "deps", ""):
        deps = [d.strip() for d in args.deps.split(",") if d.strip()]

    create_library(
        name=name,
        version=getattr(args, "version", GlobalConfig.VERSION),
        namespace=getattr(args, "namespace", None),
        deps=deps,
        header_only=getattr(args, "header_only", False),
        interface=getattr(args, "interface", False),
        modules=getattr(args, "modules", False),
        template=getattr(args, "template", ""),
        cxx_standard=getattr(args, "cxx_standard", ""),
        link_app=getattr(args, "link_app", False),
        dry_run=getattr(args, "dry_run", False),
        root=PROJECT_ROOT,
    )


def _impl_cmd_remove(args) -> None:
    name = args.name
    delete = getattr(args, "delete", False)
    dry = getattr(args, "dry_run", False)
    try:
        remove_library(name=name, delete=delete, dry_run=dry, root=PROJECT_ROOT)
    except FileNotFoundError:
        print("Not found:", name)
        return
    except ValueError as e:
        print(str(e))
        return


def _impl_cmd_rename(args) -> None:
    old = args.old
    new = args.new
    dry = getattr(args, "dry_run", False)
    try:
        rename_library(old=old, new=new, dry_run=dry, root=PROJECT_ROOT)
    except FileNotFoundError:
        print("Not found:", old)
        return
    except FileExistsError:
        print("Destination exists:", new)
        return
    except ValueError as e:
        print(str(e))
        return


def _impl_cmd_move(args) -> None:
    name = args.name
    dest = args.dest
    dry = getattr(args, "dry_run", False)
    try:
        move_library(name=name, dest=dest, dry_run=dry, root=PROJECT_ROOT)
    except FileNotFoundError:
        print("Not found:", name)
        return
    except FileExistsError:
        print("Destination exists:", dest)
        return
    except ValueError as e:
        print(str(e))
        return


def _impl_cmd_deps(args) -> None:
    name = args.name
    lib_dir = LIBS_DIR / name
    if not lib_dir.exists():
        print("Not found:", name)
        raise SystemExit(2)
    deps_file = lib_dir / "deps.txt"
    if getattr(args, "add", ""):
        deps_file.write_text((deps_file.read_text(encoding="utf-8") if deps_file.exists() else "") + args.add + "\n",
                              encoding="utf-8")
        print("Added dependency", args.add)
        return
    if getattr(args, "remove", ""):
        if deps_file.exists():
            lines = [line for line in deps_file.read_text(encoding="utf-8").splitlines() if line.strip() != args.remove]
            deps_file.write_text("\n".join(lines), encoding="utf-8")
        print("Removed dependency", args.remove)
        return
    if getattr(args, "add_url", ""):
        url = args.add_url
        via = getattr(args, "via", "fetchcontent")
        if via == "fetchcontent":
            m = re.search(r'([^/]+?)(?:\.git)?(?:@.*)?$', url)
            depname = (m.group(1) if m else "external_dep").replace('-', '_')
            deps_cmake = lib_dir / "deps.cmake"
            if _USE_JINJA_LIBCMD:
                content = _render_template_file("deps_fetchcontent.jinja2", url=url, depname=depname)
            else:
                content = (
                    f"# Auto-generated FetchContent for {url}\n"
                    "include(FetchContent)\n"
                    f"FetchContent_Declare(\n    {depname}\n    URL \"{url}\"\n)\n"
                    f"FetchContent_MakeAvailable({depname})\n"
                )
            deps_cmake.write_text(content, encoding="utf-8")
            cm = lib_dir / "CMakeLists.txt"
            if cm.exists():
                cm_text = cm.read_text(encoding="utf-8")
                if "deps.cmake" not in cm_text:
                    cm.write_text("include(\"${CMAKE_CURRENT_LIST_DIR}/deps.cmake\")\n\n" + cm_text, encoding="utf-8")
            print("Added external URL dependency (FetchContent) ->", deps_cmake)
            return
        else:
            deps_file.write_text((deps_file.read_text(encoding="utf-8") if deps_file.exists() else "") + url + "\n",
                                  encoding="utf-8")
            print(f"Recorded external dependency ({via}) -> deps.txt")
            return
    print("deps: simplified implementation — use direct CMake edits for complex cases")


def _impl_cmd_info(args) -> None:
    name = args.name
    lib_dir = LIBS_DIR / name
    if not lib_dir.exists():
        print("Not found:", name)
        return

    print(f"Library: {name}")
    print(f"Path: {lib_dir.relative_to(PROJECT_ROOT)}")

    cm = lib_dir / "CMakeLists.txt"
    if cm.exists():
        content = cm.read_text(encoding="utf-8")
        ver_m = re.search(r'project\s*\(.*VERSION\s+([\d.]+)', content, re.IGNORECASE)
        if ver_m:
            print(f"Version: {ver_m.group(1)}")

    deps = _get_lib_deps(name)
    if deps:
        print(f"Dependencies: {', '.join(deps)}")
    else:
        print("Dependencies: None")

    print("\nFiles:")
    for p in sorted(lib_dir.rglob("*")):
        if p.is_file():
            print(f"  - {p.relative_to(lib_dir)}")


def _impl_cmd_test(args) -> None:
    name = args.name
    preset = getattr(args, "preset", None)
    if preset:
        run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "build", "--preset", preset])
        try:
            run_proc(["cmake", "--build", "--preset", preset, "--target", f"{name}_tests"])
        except SystemExit:
            raise
    else:
        run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "build", "check"])


def _impl_cmd_export(args) -> None:
    name = args.name
    try:
        from core.libpkg import export as lib_export
    except Exception:
        lib_export = None

    lib_dir = LIBS_DIR / name
    if not lib_dir.exists():
        print("Not found:", name)
        return

    dry = getattr(args, "dry_run", False)
    if lib_export:
        try:
            path = lib_export.create_export_snippet(name, root=PROJECT_ROOT, dry_run=dry)
            if dry:
                return
            print("Wrote install/export helper:", path)
            print("Tip: include this file from your top-level CMake install step or CPack configuration.")
            return
        except FileNotFoundError:
            print("Not found:", name)
            return
        except Exception as e:
            print("export: failed to generate advanced export files:", e)

    install_file = lib_dir / "install.cmake"
    if _USE_JINJA_LIBCMD:
        content = _render_template_file("install_snippet.jinja2", name=name)
    else:
        content = (
            f"# Install/export snippet for {name}\n"
            f"install(TARGETS {name}\n"
            "    EXPORT {name}Targets\n"
            "    ARCHIVE DESTINATION lib\n"
            "    LIBRARY DESTINATION lib\n"
            "    RUNTIME DESTINATION bin\n"
            ")\n\n"
            f"install(EXPORT {name}Targets FILE {name}Targets.cmake NAMESPACE {name}:: DESTINATION lib/cmake/{name})\n"
        )
    if dry:
        print("Dry-run: would create:", install_file)
        print("---\n" + content)
        return
    install_file.write_text(content, encoding="utf-8")
    print("Wrote install snippet:", install_file)
    print("Tip: include or add this to your top-level install step or CPack configuration.")


def _impl_cmd_lib_upgrade_std(args) -> None:
    name = getattr(args, "name")
    std = getattr(args, "std")
    dry = getattr(args, "dry_run", False)
    lib_cm = LIBS_DIR / name / "CMakeLists.txt"
    if not lib_cm.exists():
        print(f"Library '{name}' not found at {lib_cm}")
        raise SystemExit(1)
    content = lib_cm.read_text(encoding="utf-8")
    new_content = re.sub(r'(CXX_STANDARD\s+)\d+', rf'\g<1>{std}', content)
    if new_content == content:
        print(f"[no change] No CXX_STANDARD setting found in {lib_cm.relative_to(PROJECT_ROOT)}")
        return
    if dry:
        print(f"[dry-run] Would upgrade {lib_cm.relative_to(PROJECT_ROOT)} to C++{std}")
    else:
        lib_cm.write_text(new_content, encoding="utf-8")
        print(f"Upgraded {lib_cm.relative_to(PROJECT_ROOT)} to C++{std}")


# ── CLIResult wrapper functions ───────────────────────────────────────────────

def cmd_lib_upgrade_std(args):
    return wrap_command(_impl_cmd_lib_upgrade_std, args)


def cmd_list(args):
    return wrap_command(_impl_cmd_list, args)


def cmd_tree(args):
    return wrap_command(_impl_cmd_tree, args)


def cmd_doctor(args):
    return wrap_command(_impl_cmd_doctor, args)


def cmd_add(args):
    return wrap_command(_impl_cmd_add, args)


def cmd_remove(args):
    if getattr(args, "delete", False) and not GlobalConfig.YES and not getattr(args, "dry_run", False):
        try:
            resp = input(f"Confirm delete of library '{getattr(args, 'name', '')}' and its files? [y/N]: ")
        except Exception:
            resp = "n"
        if resp.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return CLIResult(success=False, code=1, message="User aborted")
    return wrap_command(_impl_cmd_remove, args)


def cmd_rename(args):
    return wrap_command(_impl_cmd_rename, args)


def cmd_move(args):
    return wrap_command(_impl_cmd_move, args)


def cmd_deps(args):
    return wrap_command(_impl_cmd_deps, args)


def cmd_info(args):
    return wrap_command(_impl_cmd_info, args)


def cmd_test(args):
    return wrap_command(_impl_cmd_test, args)


def cmd_export(args):
    return wrap_command(_impl_cmd_export, args)
