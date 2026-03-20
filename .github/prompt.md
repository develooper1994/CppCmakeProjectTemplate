# Project AI Prompt

## Purpose
This repository is a **C++ / CMake multi-target template** designed for long-term scalability and AI-assisted development.

## Structure
- libs/ → internal libraries
- apps/ → executables
- external/ → vendor dependencies (isolated)
- tests/ → GoogleTest
- docs/ → documentation
- cmake/ → shared modules
- scripts/ → automation

## Core Rules

### 1. External Isolation
- NEVER modify external/
- ALWAYS use:
  - add_subdirectory(... SYSTEM)
  - FetchContent(SYSTEM)
- No warnings applied to vendor code

### 2. Internal Code Policy
- Strict warnings enabled
- target-based CMake only
- No global compile flags

### 3. Build System
- CMake 3.25+
- Presets required
- compile_commands.json must exist
- Unity build OFF by default

### 4. Options
- BUILD_SHARED_LIBS
- ENABLE_SANITIZERS
- ENABLE_LTO
- ENABLE_CCACHE

### 5. Versioning
Uses Git:
- git describe
- commit hash
- branch
- dirty state

Accessible via:
--version
--buildinfo

### 6. Documentation
- Doxygen
- MkDocs
- docs target

### 7. Testing
- GoogleTest
- CTest integration

---

## AI Rules

### DO:
- follow structure
- update CMake when adding targets
- add docs + tests
- keep build valid

### DO NOT:
- modify vendor code
- flatten project
- break presets
- disable compile_commands

---

## Target Creation Contract

Every new target MUST include:
- CMakeLists.txt
- README.md
- docs/
- proper linking
- optional tests

---

## Principle

> Smallest valid change that preserves build integrity
