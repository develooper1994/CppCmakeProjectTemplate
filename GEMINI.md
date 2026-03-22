# GEMINI.md — Project Overview for AI Assistants

## TL;DR

This is a **professional C++ CMake project template** with full automation tooling.
**Do not re-implement existing tools.** Use the scripts in `scripts/` to manage everything.

## Quick Reference

```bash
# Build + test (always run this after changes)
python3 scripts/build.py check --no-sync

# Add a library
python3 scripts/toollib.py add my_lib

# All library management
python3 scripts/toollib.py --help

# Project-level management (presets, toolchains, repos)
python3 scripts/toolsolution.py --help

# Check health
python3 scripts/toollib.py doctor
python3 scripts/toolsolution.py doctor
```

## Repository Structure

```
apps/           Executable apps (main_app prints full build info at runtime)
libs/           Libraries — each independent, versioned, with its own BuildInfo
tests/unit/     GoogleTest per-library test suites
cmake/          CMake modules + auto-generated C++ headers:
  ProjectInfo.h         → single include for all build metadata
  BuildInfoHelper.h     → BUILD_INFO_PRINT_ALL, BUILD_INFO_VERSION_LINE macros
  FeatureFlags.h        → auto-generated, exposes all ENABLE_* as #define + constexpr array
scripts/
  toollib.py            → library CRUD (add/remove/rename/move/deps/export/info/test)
  toolsolution.py       → solution orchestration (presets/toolchains/repo/test/upgrade-std)
  build.py              → build/check/clean/deploy/extension
  common.py             → shared utilities
  install_deps.py       → dependency checker/installer
extension/      VS Code extension (C++ CMake Scaffolder)
docs/
  PLANS.md      → pending feature roadmap
  EMBEDDED.md   → embedded development guide
```

## Key Design Principles

1. **Target-based CMake** — no global flags, everything scoped to targets
2. **Per-library versioning** — each lib can have independent version via `target_generate_build_info`
3. **Compile-time feature detection** — `FeatureFlags.h` auto-generated from `PROJECT_ALL_OPTIONS`
4. **MSVC runtime consistency** — `/MT` vs `/MD` set automatically from `BUILD_SHARED_LIBS`
5. **Cross-platform presets** — `CMakePresets.json` covers GCC/Clang/MSVC/ARM/embedded

## Adding Things

| What | How |
|---|---|
| New library | `toollib.py add <n> [--header-only\|--interface]` |
| External dep | `toollib.py deps <n> --add-url <url>@<tag> [--via vcpkg\|conan]` |
| New preset | `toolsolution.py preset add --compiler gcc --type debug --link static --arch x86_64` |
| New toolchain | `toolsolution.py toolchain add --name stm32 --template arm-none-eabi --cpu cortex-m4 --gen-preset` |
| find_package support | `toollib.py export <n>` |
| Git submodule | `toolsolution.py repo add-submodule --url <url> --dest libs/<n>` |

## Execution Protocol (same as AGENTS.md)

Analyze → Impact → Plan → Implement → Integrate → Validate → Output

Always end with: `python3 scripts/build.py check --no-sync`
