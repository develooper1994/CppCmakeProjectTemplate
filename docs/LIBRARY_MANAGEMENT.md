# Library Management

All library operations go through `scripts/tool.py lib` (use the `lib` subcommand).
**In VS Code:** `Ctrl+Shift+P` → *CppTemplate: Library Manager*

```bash
# Create a new library
python3 scripts/tool.py lib add my_lib
python3 scripts/tool.py lib add renderer --deps core,math --link-app --cxx-standard 20

# Remove a library (--delete also removes files from disk)
python3 scripts/tool.py lib remove my_lib --delete

Note: `--delete` is destructive. The CLI will prompt for confirmation unless you pass `--yes` to auto-confirm or use `--dry-run` to preview the actions. Programmatic calls to the library API (tests or scripts) bypass the interactive prompt.

# Rename (updates all source files, headers, and CMake references)
python3 scripts/tool.py lib rename old_name new_name

# Move to a subdirectory
python3 scripts/tool.py lib move renderer graphics/renderer

Note: As of v1.0.0+, `tool lib move` now also moves the library's tests directory (`tests/unit/<name>`), updates the `tests/unit/CMakeLists.txt` registration to the new path, and — when the destination basename differs from the original library name — performs in-place token replacement inside moved library and test files and updates CMake target references. Use `--dry-run` to preview the actions before applying them.

# Edit dependencies of an existing library
python3 scripts/tool.py lib deps renderer --add math --remove old_dep

# Show detailed info about a library
python3 scripts/tool.py lib info dummy_lib

# Add external dependency (FetchContent / vcpkg / conan)
python3 scripts/tool.py lib deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1
python3 scripts/tool.py lib deps my_lib --add-url https://github.com/nlohmann/json@3.11.3 --target nlohmann_json::nlohmann_json
python3 scripts/tool.py lib deps my_lib --add-url fmt --via vcpkg
python3 scripts/tool.py lib deps my_lib --add-url fmt/10.2.1 --via conan

# Build and run a single library's tests
python3 scripts/tool.py lib test dummy_lib
python3 scripts/tool.py lib test dummy_lib --preset clang-debug-static-x86_64

# List / tree / health check
python3 scripts/tool.py lib list
python3 scripts/tool.py lib tree
python3 scripts/tool.py lib doctor
```

Append `--dry-run` to any command to preview changes without applying them.

## Rename / Move / Remove (behavior details)

- **`rename`**
  - Updates source files, headers, and CMake target references atomically (uses the repository `Transaction` helper for backup and rollback).
  - Supports `--dry-run` to preview changes. Programmatic calls (tests/scripts) bypass interactive prompts.

- **`move`**
  - Moves the library directory under `libs/` and its test directory under `tests/unit/`.
  - Updates `libs/CMakeLists.txt` and `tests/unit/CMakeLists.txt` registrations to the new paths.
  - If the destination basename differs from the original library name, the tool can perform token replacement inside moved files and update CMake target references so targets remain consistent.
  - Use `--dry-run` to preview the changes before applying them; supply `--yes` to skip interactive confirmation when invoking the command non-interactively.

- **`remove`**
  - By default detaches the library from CMake registration; with `--delete` it deletes files from disk.
  - After deletion, empty parent directories under `libs/` and `tests/unit/` are pruned to avoid orphaned folders.
  - The CLI prompts for destructive `--delete` actions unless `--yes` is supplied; use `--dry-run` to preview first.

Each library gets its own independent version via `target_generate_build_info`:

```cmake
# libs/my_lib/CMakeLists.txt
target_generate_build_info(my_lib
    NAMESPACE my_lib_info
    PROJECT_VERSION "2.0.0"   # independent from solution version
)
```

## New Capabilities (v1.0.0+)

- **Header-only / Interface Libs:** `python3 scripts/tool.py lib add my_lib --header-only`
- **Export Config:** `python3 scripts/tool.py lib export my_lib` (creates cmake config for find_package)
- **URL Dependencies:** `python3 scripts/tool.py lib deps my_lib --add-url https://...` (FetchContent/vcpkg/conan)
- **Repo Management:** `python3 scripts/tool.py sol repo ...` (submodules & fetch deps)

For plugin details see: [Plugins](PLUGINS.md)
