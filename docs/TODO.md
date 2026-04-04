# CppCmakeProjectTemplate — Remaining Work (Gap Analysis)

> Generated from a comprehensive gap analysis of the entire codebase.
> 232 tests passing. All 23 CLI commands functional. All 6 plugins well-formed.
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

## ✅ Completed — MEDIUM Priority

### ~~1. `config_schema.py` — False Validation Warnings~~ ✅

Fixed: Added 4 missing `[doc]` keys, `version`/`description` to `_LIB_KEYS`, `description` to `_APP_KEYS`.

### ~~2. Generator Missing WASM Toolchain Tracking~~ ✅

Fixed: Added `"wasm32-emscripten.cmake"` to `STATIC_TOOLCHAIN_FILES`.

### ~~3. USAGE.md — Incomplete Command Table~~ ✅

Fixed: Added 7 missing commands to overview table, updated section count to "20+", added 6 detailed new sections (SBOM, Diagnostics, Migration, Nix, Templates, Plugins).

### ~~4. Missing Tests for New Commands~~ ✅

Added 80 new tests across 5 files:
- `test_nix.py` — 13 tests (flake content + CLI)
- `test_sbom.py` — 17 tests (dependency detection, SPDX, CycloneDX, CLI)
- `test_diagnostics.py` — 17 tests (10 regex patterns, dedup, formatting, CLI)
- `test_migrate.py` — 17 tests (manifest, drift detection, upgrade, CLI)
- `test_templates.py` — 16 tests (data structure, list, create, CLI)

---

## ✅ Completed — LOW Priority

### ~~5. AGENTS.md Core Commands List Incomplete~~ ✅

Fixed: Updated the list to include all 23 command modules.

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
