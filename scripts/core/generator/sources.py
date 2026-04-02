"""
core/generator/sources.py — C++ source file scaffolding.

Generates from [[project.libs]] and [[project.apps]] in tool.toml:
  - libs/<name>/src/<name>.cpp
  - libs/<name>/include/<name>/<name>.h
  - libs/<name>/README.md
  - apps/<name>/src/main.cpp
  - tests/unit/<name>/<name>_test.cpp
  - tests/fuzz/fuzz_<name>.cpp  (if lib.fuzz == true)
  - VERSION
  - README.md
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

if __name__ != "__main__":
    from core.generator.engine import ProjectContext


# ---------------------------------------------------------------------------
# Library scaffolding
# ---------------------------------------------------------------------------

def _gen_lib_header(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    lib_type = lib.get("type", "normal")
    is_header_only = lib_type in ("header-only", "interface")
    has_export = lib.get("export", False)

    parts = [
        "#pragma once",
        "",
        "#include <string>",
    ]

    if has_export and not is_header_only:
        parts.append(f'#include "{name}/{name}_export.h"')

    parts.extend(["", f"namespace {ns} {{", ""])

    export_macro = f"{name.upper()}_EXPORT " if (has_export and not is_header_only) else ""
    parts.append(f"{export_macro}std::string get_name();")

    parts.extend(["", f"}} // namespace {ns}", ""])
    return "\n".join(parts)


def _gen_lib_source(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name

    return f'''\
#include "{name}/{name}.h"

namespace {ns} {{

// cppcheck-suppress unusedFunction
std::string get_name() {{
    return "{name}";
}}

}} // namespace {ns}
'''


def _gen_lib_readme(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    lib_type = lib.get("type", "normal")
    return f"""\
# {name}

{lib_type.capitalize()} library — part of {ctx.name}.

## Usage

```cpp
#include "{name}/{name}.h"

auto value = {name}::get_name();
```
"""


# ---------------------------------------------------------------------------
# Application scaffolding
# ---------------------------------------------------------------------------

def _gen_app_main(app: dict[str, Any], ctx: ProjectContext) -> str:
    name = app["name"]
    deps = app.get("deps", [])
    build_info = app.get("build_info", False)
    gui = app.get("gui", False)

    includes = ["#include <iostream>"]

    if build_info:
        includes.append('#include "ProjectInfo.h"')

    for dep in deps:
        includes.append(f'#include "{dep}/{dep}.h"')

    parts = ["\n".join(includes), ""]

    if gui:
        parts.append(f"""\
int main(int argc, char* argv[]) {{
    (void)argc;
    (void)argv;
""")
    else:
        parts.append("int main() {")

    if build_info:
        parts.append(f"    BUILD_INFO_PRINT_ALL(std::cout, {name}_info);")

    for dep in deps:
        parts.append(f'    std::cout << {dep}::get_name() << "\\n";')

    parts.extend(["    return 0;", "}", ""])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------

def _gen_unit_test(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    suite = "".join(w.capitalize() for w in name.split("_")) + "Test"

    return f'''\
#include "{name}/{name}.h"

#include <gtest/gtest.h>
#include <string>

TEST({suite}, GetNameIsNotEmpty) {{
    EXPECT_FALSE({ns}::get_name().empty());
}}

TEST({suite}, GetNameReturnsExpected) {{
    EXPECT_EQ({ns}::get_name(), "{name}");
}}
'''


def _gen_fuzz_harness(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name

    return f'''\
#include <cstddef>
#include <cstdint>

#include "{name}/{name}.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {{
    if (size == 0) return 0;
    // TODO: Call {ns} APIs with fuzz data
    (void)data;
    return 0;
}}
'''


# ---------------------------------------------------------------------------
# Root files
# ---------------------------------------------------------------------------

def _gen_version(ctx: ProjectContext) -> str:
    return ctx.version + "\n"


def _gen_root_readme(ctx: ProjectContext) -> str:
    return f"""\
# {ctx.name}

{ctx.description}

## Build

```bash
python3 scripts/tool.py build
```

## Test

```bash
python3 scripts/tool.py build check
```

## License

{ctx.license}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}

    # Root files
    files["VERSION"] = _gen_version(ctx)
    files["README.md"] = _gen_root_readme(ctx)

    for lib in ctx.libs:
        name = lib["name"]
        lib_type = lib.get("type", "normal")
        is_header_only = lib_type in ("header-only", "interface")

        # Header
        files[f"libs/{name}/include/{name}/{name}.h"] = _gen_lib_header(lib, ctx)

        # Source (not for header-only)
        if not is_header_only:
            files[f"libs/{name}/src/{name}.cpp"] = _gen_lib_source(lib, ctx)

        # README
        files[f"libs/{name}/README.md"] = _gen_lib_readme(lib, ctx)

        # Unit test
        if ctx.tests.get("auto_generate", True):
            files[f"tests/unit/{name}/{name}_test.cpp"] = _gen_unit_test(lib, ctx)

        # Fuzz harness
        if lib.get("fuzz") and ctx.tests.get("fuzz"):
            files[f"tests/fuzz/fuzz_{name}.cpp"] = _gen_fuzz_harness(lib, ctx)

    for app in ctx.apps:
        name = app["name"]
        files[f"apps/{name}/src/main.cpp"] = _gen_app_main(app, ctx)

    return files
