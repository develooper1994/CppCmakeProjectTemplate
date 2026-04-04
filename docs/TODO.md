# CppCmakeProjectTemplate — Remaining Work (Gap Analysis)

> Generated from a comprehensive gap analysis of the entire codebase.
> 152 tests passing. All 23 CLI commands functional. All 6 plugins well-formed.
> Use this document to pick up where you left off.

---

## Overall Health

The project is fundamentally sound:

- **No dead imports** — all `import` statements resolve correctly
- **No stub commands** — all 23 registered CLI commands have working implementations
- **No broken CI references** — all script paths in `.github/workflows/` are valid
- **CAPABILITIES.md is accurate** — every claimed feature actually exists and works
- **All 11 generator components are functional**
- **All 6 plugins have `PLUGIN_META` + `main()` and work correctly**

---

## MEDIUM Priority — Should Fix

### 1. `config_schema.py` — False Validation Warnings

**File:** `scripts/core/utils/config_schema.py`

The schema validator (`tool validate`) produces false "unknown key" warnings for legitimate keys:

| Section | Missing Keys | Impact |
|---------|-------------|--------|
| `[doc]` | `generate_api_docs`, `doxygen_dot`, `doxygen_extract_all`, `mkdocs_theme` | 4 false warnings |
| `[[project.libs]]` | `version`, `description` | Warns on `dummy_lib` version field and template-generated libs |
| `[[project.apps]]` | `description` | Warns on template-generated apps |

**Fix:** Add the missing keys to `_DOC_KEYS`, `_LIB_KEYS`, and `_APP_KEYS` in `config_schema.py`. Small effort (~10 lines each).

### 2. Generator Missing WASM Toolchain Tracking

**File:** `scripts/core/generator/cmake_static/__init__.py`

The file `cmake/toolchains/wasm32-emscripten.cmake` exists on disk but is **not listed** in `STATIC_TOOLCHAIN_FILES`. This means `tool generate` will not reproduce it — the file would be lost if you deleted and regenerated the project.

**Fix:** Add `"wasm32-emscripten.cmake"` to `STATIC_TOOLCHAIN_FILES`. One line.

### 3. USAGE.md — Incomplete Command Table

**File:** `docs/USAGE.md`

The command overview table lists only 16 commands. Missing from the table and/or body:

- `sbom` — SPDX/CycloneDX bill-of-materials generation
- `diagnostics` — Build error pattern matching
- `nix` — Nix flake generation
- `migrate` — Manifest-based drift detection & upgrade
- `templates` — Built-in project templates
- `presets` — CMake preset management
- `plugins` — Plugin system
- `tui` — Terminal UI launcher

Also, the "9 sections" claim for `tool.toml` configuration is stale — actual count is 16+ sections.

**Fix:** Add the missing commands to the table and update the section count. Small effort.

### 4. Missing Tests for New Commands

These commands are fully implemented but have **zero test coverage**:

| Command | What It Does | Test Effort |
|---------|-------------|-------------|
| `sbom.py` | SPDX + CycloneDX JSON generation, multi-source detection | medium |
| `diagnostics.py` | 9 error patterns, `--log` and `--check` modes | medium |
| `migrate.py` | Drift detection, manifest-based incremental upgrade | medium |
| `templates.py` | 7 built-in templates, `list` + `create` subcommands, config merge | medium |
| `nix.py` | Generates `flake.nix` + `.envrc` from tool.toml | small |

**Recommendation:** Write unit tests mocking filesystem/subprocess calls. Each command is self-contained, so tests can be independent. ~20-30 tests total.

---

## LOW Priority — Nice to Have

### 5. AGENTS.md Core Commands List Incomplete

**File:** `AGENTS.md` (line ~27)

The "Core Logic" line says `(build, lib, sol, generate, new, adopt, validate, completion, license)` but the actual `scripts/core/commands/` directory has 23 modules. Missing from the list: `deps`, `doc`, `format`, `perf`, `presets`, `release`, `security`, `session`, `plugins`, `sbom`, `diagnostics`, `nix`, `migrate`, `templates`.

**Fix:** Update the list. Trivial.

### 6. Missing Tests for Ancillary Features

| Feature | File | Test Effort |
|---------|------|-------------|
| `setup.py --check`, `--detect`, `--category` modes | `scripts/plugins/setup.py` | medium |
| `deps.py update` subcommand | `scripts/core/commands/deps.py` | small |
| `build watch` / `build diagnose` subcommands | `scripts/core/commands/build/commands.py` | medium |
| `agents.py` generator component | `scripts/core/generator/agents.py` | small |

### 7. No Windows/macOS CI Matrix

**File:** `.github/workflows/ci.yml`

All CI workflows target `ubuntu-latest` only. MSVC and AppleClang presets are fully implemented and tested in unit tests, but are **never exercised in actual CI**. Adding `windows-latest` and `macos-latest` to the matrix would validate cross-platform presets for real.

**Effort:** Large — requires dealing with platform-specific dependency installation, toolchain availability, and matrix explosion.

---

## Confirmed NOT Gaps

These were investigated and found to be working correctly:

- **`cmake-static` silently skips missing files** — intentional graceful degradation, not a bug
- **`ci` and `configs` components use read-and-track** (not generate) — by design for hand-maintained files
- **`ci` component dynamically discovers workflows** via `wf_dir.iterdir()` — well-designed
- **winget/choco maps** are substantive (11 and 10 entries respectively) — missing entries are tools that genuinely don't exist on Windows (valgrind, lcov, gcovr)
- **MSVC/AppleClang presets** generate correctly with proper skip rules and arch maps

---

## Quick Win Checklist

If you want to make fast progress, do these in order:

1. [x] Fix `config_schema.py` — add missing keys to `_DOC_KEYS`, `_LIB_KEYS`, `_APP_KEYS` (~15 min)
2. [x] Add `wasm32-emscripten.cmake` to `STATIC_TOOLCHAIN_FILES` (~2 min)
3. [x] Update AGENTS.md core commands list (~5 min)
4. [ ] Update USAGE.md command table + section count (~30 min)
5. [ ] Write tests for `nix.py` (smallest scope) (~30 min)
6. [ ] Write tests for remaining 4 commands (~2-3 hours total)

---

## Related Documents

- [ROADMAP.md](ROADMAP.md) — Future ideas and backlog (Custom Templates, Monorepo, Plugin v2, etc.)
- [CAPABILITIES.md](CAPABILITIES.md) — Completed and verified features
- [USAGE.md](USAGE.md) — CLI reference (needs updates per item 3 above)
- [DEPENDENCIES.md](DEPENDENCIES.md) — Cross-platform dependency tables
