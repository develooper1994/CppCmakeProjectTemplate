# CI / Quality Guards

## Pre-commit hooks

```bash
python3 scripts/setup_hooks.py
```

Runs: clang-format, clang-tidy, secret scanner on every commit.

## CI matrix

Four jobs run on every push (`.github/workflows/ci.yml`):

| Job | OS | Compiler |
|---|---|---|
| `build-linux` | Ubuntu | GCC 13 |
| `build-linux-clang` | Ubuntu | Clang |
| `build-windows` | Windows | MSVC 2022 |
| `build-macos` | macOS | AppleClang |

## Manual CI simulation

```bash
python3 scripts/tool.py sol doctor
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
