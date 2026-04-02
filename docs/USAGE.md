# CLI Usage Reference

Complete command reference for `python3 scripts/tool.py`.

---

## Command Overview

| Command | Purpose |
|---------|---------|
| `new` | Interactive project creation wizard |
| `generate` | Generate project from `tool.toml` (profiles, feature toggles) |
| `build` | Build, check, clean, deploy |
| `lib` | Library management (add, remove, list, rename, move) |
| `sol` | Project orchestration (presets, toolchains, CI, doctor) |
| `license` | License recommendation and selection |
| `release` | Versioning and publishing |
| `perf` | Performance analysis and tuning |
| `security` | Security scanning and CVE auditing |
| `format` | Code formatting and static analysis |
| `deps` | Dependency manager operations |
| `doc` | Documentation build and serve |
| `session` | Session state save/load |

Global flags: `--json` (machine-readable output), `--yes` (non-interactive), `--dry-run` (preview).

---

## Project Creation

### Interactive Wizard

```bash
python3 scripts/tool.py new MyProject
```

Prompts for name, author, license, C++ standard, profile, libraries, apps, and features.

### Non-Interactive (CI)

```bash
python3 scripts/tool.py new MyProject --non-interactive
```

### Profile-Based Generation

```bash
python3 scripts/tool.py generate --profile library --target-dir ./MyLib
python3 scripts/tool.py generate --profile minimal --with ci --without fuzz
python3 scripts/tool.py generate --explain          # preview effective settings
```

Profiles: `full` (default), `minimal`, `library`, `app`, `embedded`.

### Generator Debug & Observability

```bash
python3 scripts/tool.py generate --debug       # per-component timing + tracebacks
python3 scripts/tool.py generate --verbose      # progress logging
python3 scripts/tool.py generate --json         # machine-readable JSON output
```

See also: [STARTING_PROJECT.md](STARTING_PROJECT.md)

---

## Build System

```bash
python3 scripts/tool.py build                  # configure + build (auto-detects preset)
python3 scripts/tool.py build check            # build + test + validate
python3 scripts/tool.py build check --no-sync  # skip dependency sync
python3 scripts/tool.py build clean            # clean build directory
python3 scripts/tool.py build clean --all      # clean all build artifacts
python3 scripts/tool.py build extension        # package VS Code extension (.vsix)
python3 scripts/tool.py build docker           # build inside container
python3 scripts/tool.py build deploy --host <H> --path <P>  # remote deploy
```

### Presets & Sanitizers

```bash
python3 scripts/tool.py build --preset gcc-release-static-x86_64
python3 scripts/tool.py build --sanitizers asan ubsan
python3 scripts/tool.py build --sanitizers all
python3 scripts/tool.py build --allocator mimalloc
python3 scripts/tool.py build --profile extreme   # Rust-like safety
```

See also: [BUILDING.md](BUILDING.md), [BUILD_SETTINGS.md](BUILD_SETTINGS.md)

---

## Library Management

```bash
python3 scripts/tool.py lib list                  # list all libraries
python3 scripts/tool.py lib add my_lib             # add a normal library
python3 scripts/tool.py lib add my_lib --header-only
python3 scripts/tool.py lib add my_lib --interface
python3 scripts/tool.py lib add my_lib --template singleton
python3 scripts/tool.py lib remove my_lib [--delete]
python3 scripts/tool.py lib rename old_name new_name
python3 scripts/tool.py lib move my_lib --to new_dir
python3 scripts/tool.py lib deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1
python3 scripts/tool.py lib export my_lib          # find_package support
python3 scripts/tool.py lib tree                   # dependency tree
python3 scripts/tool.py lib info my_lib            # library info
python3 scripts/tool.py lib doctor                 # health check
```

See also: [LIBRARY_MANAGEMENT.md](LIBRARY_MANAGEMENT.md)

---

## Project Orchestration

```bash
python3 scripts/tool.py sol preset list           # list CMake presets
python3 scripts/tool.py sol preset generate       # generate from tool.toml
python3 scripts/tool.py sol ci                    # run CI locally
python3 scripts/tool.py sol doctor                # project health check
python3 scripts/tool.py sol target add my_app     # add app target
python3 scripts/tool.py sol sysroot add <arch>    # install cross-compile sysroot
```

See also: [PROJECT_ORCHESTRATION.md](PROJECT_ORCHESTRATION.md)

---

## Performance

```bash
python3 scripts/tool.py perf track                # save baseline
python3 scripts/tool.py perf check-budget         # compare vs baseline
python3 scripts/tool.py perf size                  # binary size analysis
python3 scripts/tool.py perf build-time            # Ninja log analysis
python3 scripts/tool.py perf stat                  # perf stat wrapper
python3 scripts/tool.py perf record                # flame graph
python3 scripts/tool.py perf valgrind [--vg-tool memcheck|massif]
python3 scripts/tool.py perf concurrency           # helgrind/DRD
python3 scripts/tool.py perf vec                   # vectorization report
python3 scripts/tool.py perf godbolt               # Compiler Explorer
python3 scripts/tool.py perf graph                 # dependency graph
python3 scripts/tool.py perf autotune [--repeat N] # auto-tuning
python3 scripts/tool.py perf promote               # promote winning flags
python3 scripts/tool.py perf hw-recommend           # CPU-aware recommendations
python3 scripts/tool.py perf size-diff              # binary delta tracking
```

See also: [PERFORMANCE.md](PERFORMANCE.md)

---

## Security & Quality

```bash
python3 scripts/tool.py security scan             # OSV-Scanner + Cppcheck
python3 scripts/tool.py format tidy-fix            # clang-tidy --fix
python3 scripts/tool.py format iwyu [--target <lib>] [--fix]
python3 scripts/tool.py deps lock                  # generate lock files
python3 scripts/tool.py deps verify                # check staleness
```

See also: [CI.md](CI.md)

---

## Release & Licensing

```bash
python3 scripts/tool.py release bump patch|minor|major
python3 scripts/tool.py release tag
python3 scripts/tool.py release publish --to github|conan|vcpkg
python3 scripts/tool.py license recommend          # interactive decision tree
python3 scripts/tool.py license list               # show supported licenses
python3 scripts/tool.py license recommend --apply  # write to tool.toml
```

---

## Documentation

```bash
python3 scripts/tool.py doc serve [--port N] [--open]  # live server
python3 scripts/tool.py doc build                      # mkdocs/sphinx
```

---

## Setup & Verification

```bash
python3 scripts/tool.py setup --install           # install dependencies
python3 scripts/tool.py setup --env               # create Python venv
python3 scripts/tool.py verify                     # full verification harness
python3 scripts/tool.py sol doctor                 # health check
```

---

## Configuration

All settings live in `tool.toml` with 9 sections: `tool`, `build`, `perf`, `security`, `lib`, `doc`, `release`, `hooks`, `embedded`.

CLI args override `tool.toml`. Runtime state persists in `[session]`.

```bash
python3 scripts/tool.py session save
python3 scripts/tool.py session load
python3 scripts/tool.py session set key value
```
