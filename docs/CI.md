# CI / Quality Guards

## Pre-commit hooks

```bash
# One-time setup
pip install pre-commit
pre-commit install

# Run all hooks manually
pre-commit run --all-files

# Optional: install repo hook templates into .git/hooks/
python3 scripts/tool.py hooks --install
```

Runs on every commit: `gitleaks` (secrets), `ruff` + `ruff-format` (Python), `cmake-format` + `cmake-lint`, `clang-format` (C/C++), and general hygiene checks.

## CI matrix

The following jobs run on push / PR to `main` (`.github/workflows/ci.yml`):

| Job | OS | Purpose |
| --- | --- | --- |
| `python-tests` | Ubuntu | Python tests + template smoke-run |
| `detect-changes` | Ubuntu | Detect changed C/C++ paths (gates C++ jobs) |
| `cpp-build` | Ubuntu | Full verification via `tool.py build check --no-sync` |
| `build-linux-gcc` | Ubuntu | GCC preset matrix (debug + release) |
| `build-linux-clang` | Ubuntu | Clang preset matrix (debug + release) |
| `build-windows` | Windows | MSVC preset matrix (debug + release) |
| `build-macos` | macOS 13 | AppleClang x86_64 (`clang-debug-static-x86_64`) |

## Manual CI simulation

```bash
python3 scripts/tool.py sol doctor
python3 scripts/tool.py build check --no-sync
ctest --preset gcc-debug-static-x86_64 --output-on-failure
```

## TUI (Terminal User Interface)

A full-screen terminal UI wrapping all tooling:

```bash
# Install textual (one-time)
pip3 install textual --break-system-packages

# Launch TUI (choose one)
python3 scripts/tui.py
python3 -m scripts.tui
# or via dispatcher
python3 scripts/tool.py tui
```

Tabs: 🔨 Build / 📚 Libraries / ⚙ Project / ℹ Info — all operations delegate to CLI tools.
