# CLI Usage Reference

Complete command reference for `python3 scripts/tool.py`.

---

## Command Overview

| Command | Purpose |
|---------|---------|
| `new` | Interactive project creation wizard |
| `generate` | Generate project from `tool.toml` (profiles, feature toggles) |
| `adopt` | In-place adoption of existing C++ projects |
| `validate` | Schema-based validation for `tool.toml` |
| `completion` | Shell completion scripts for Bash/Zsh/Fish |
| `build` | Build, check, clean, deploy |
| `lib` | Library management (add, remove, list, rename, move) |
| `sol` | Project orchestration (presets, toolchains, CI, doctor) |
| `license` | License recommendation and selection |
| `release` | Versioning and publishing |
| `perf` | Performance analysis and tuning |
| `security` | Security scanning and CVE auditing |
| `format` | Code formatting and static analysis |
| `deps` | Dependency manager operations |
| `doc` | Documentation build, serve, and generation |
| `session` | Session state save/load |
| `sbom` | Generate Software Bill of Materials (SPDX/CycloneDX) |
| `diagnostics` | Human-friendly build error diagnostics |
| `migrate` | Migration wizard for template upgrades |
| `nix` | Generate Nix flake for reproducible dev environments |
| `templates` | Project templates gallery — curated starters |
| `presets` | CMake preset generation and management |
| `plugins` | Plugin system (dynamic command extensions) |

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

## Project Adoption

```bash
python3 scripts/tool.py adopt                         # auto-detect sources, generate tool.toml + CMake
python3 scripts/tool.py adopt --dry-run                # preview without writing
```

Runs inside an existing directory with C++ sources — inverse of `tool new`.

---

## Config Validation

```bash
python3 scripts/tool.py validate                       # validate tool.toml schema
python3 scripts/tool.py validate --json                # machine-readable errors
```

Reports typos, unknown keys, type mismatches, and cross-reference issues.

---

## Shell Completion

```bash
python3 scripts/tool.py completion bash > /etc/bash_completion.d/tool
python3 scripts/tool.py completion zsh  > ~/.zsh/completions/_tool
python3 scripts/tool.py completion fish > ~/.config/fish/completions/tool.fish
```

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

## Auto-Detected Features

The system automatically detects available compilers, build tools, and environment features (e.g., ccache, sanitizers, docker, etc.).
To view all auto-detected features and environment summary, run:

```bash
python3 scripts/tool.py sol doctor --show-auto
```

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
python3 scripts/tool.py doc build                      # mkdocs/sphinx/doxygen
python3 scripts/tool.py doc list                       # list docs files
```

Documentation generation is integrated into `tool generate`. The doc engine is
configured in `tool.toml [doc]`:

```toml
[doc]
engine = "doxygen"        # "doxygen", "mkdocs", "sphinx", or a list
generate_api_docs = true  # generate Doxyfile / mkdocs.yml / conf.py
doxygen_dot = true        # Graphviz DOT graphs (requires graphviz)
mkdocs_theme = "material" # MkDocs theme (when engine includes "mkdocs")
```

Running `tool generate` with docs enabled produces:

- Markdown skeleton: `docs/index.md`, `getting-started.md`, `api-reference.md`, `contributing.md`
- **Doxygen**: `Doxyfile` (run `doxygen Doxyfile` to build API docs)
- **MkDocs**: `mkdocs.yml` (run `mkdocs serve` / `mkdocs build`)
- **Sphinx**: `docs/conf.py` + `docs/index.rst` (run `sphinx-build`)

Profiles `minimal` and `embedded` disable docs generation by default.
Override with `--with docs`.

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

All settings live in `tool.toml` with 20+ sections including: `tool`, `build`, `perf`, `security`, `lib`, `doc`, `release`, `hooks`, `presets`, `autotuner`, `gpu`, `embedded`, `session`, `project`, `ci`, `deps`, `docker`, `cmake_modules`, `vscode`, `git`, `docs`, `extension`, `generate`.

CLI args override `tool.toml`. Runtime state persists in `[session]`.

```bash
python3 scripts/tool.py session save
python3 scripts/tool.py session load
python3 scripts/tool.py session set key value
```

---

## SBOM (Software Bill of Materials)

```bash
python3 scripts/tool.py sbom                       # SPDX JSON to stdout
python3 scripts/tool.py sbom --format cyclonedx     # CycloneDX JSON
python3 scripts/tool.py sbom --output sbom.json     # write to file
```

Detects dependencies from `vcpkg.json`, `conanfile.py`, and `requirements-dev.txt`.

---

## Build Diagnostics

```bash
python3 scripts/tool.py diagnostics                 # parse build log for known errors
python3 scripts/tool.py diagnostics --log build.log  # analyze specific log file
python3 scripts/tool.py diagnostics --check          # run build and diagnose errors
```

Provides Rust-style error explanations with suggested fixes for common CMake,
compiler, and linker errors.

---

## Migration

```bash
python3 scripts/tool.py migrate                     # interactive upgrade
python3 scripts/tool.py migrate --check             # check for available upgrades
python3 scripts/tool.py migrate --dry-run           # preview changes
python3 scripts/tool.py migrate --force             # force regeneration
```

Detects drift between generated files and their current state. Supports
incremental upgrades with automatic backup of modified files.

---

## Nix Integration

```bash
python3 scripts/tool.py nix generate                # generate flake.nix + .envrc
python3 scripts/tool.py nix generate --dry-run      # preview without writing
python3 scripts/tool.py nix generate --output DIR   # custom output directory
```

Generates a Nix flake for reproducible development environments with
hermetic toolchain pinning. Also generates `.envrc` for direnv integration.

---

## Project Templates

```bash
python3 scripts/tool.py templates list              # list available templates
python3 scripts/tool.py templates create MyApp      # create from default (minimal)
python3 scripts/tool.py templates create MyApp --template application
python3 scripts/tool.py templates create MyApp --template embedded --dry-run
```

Available templates: `minimal`, `library`, `application`, `embedded`,
`networking`, `header-only`, `game-engine`.

---

## Plugins

```bash
python3 scripts/tool.py hello                       # example plugin
python3 scripts/tool.py hooks install               # install git hooks
python3 scripts/tool.py init                        # initialize project
python3 scripts/tool.py publish                     # publish VS Code extension
python3 scripts/tool.py setup --install             # install dependencies
python3 scripts/tool.py verify                      # full verification
```

Plugins are dynamically discovered from `scripts/plugins/`. Each plugin
provides `PLUGIN_META` and a `main()` entry point.
