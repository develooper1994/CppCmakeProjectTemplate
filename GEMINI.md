# GEMINI.md

## Project Overview
This repository is an **AI-Assisted C++ / CMake Project Template** definition. It contains the core instructions, standards, and execution protocols required for an AI agent to build and maintain a professional, multi-target (solution-style) C++ build system.

The project emphasizes **modern CMake practices**, **external dependency isolation**, and **rigorous build integrity**.

## Directory Structure & Intent
The current directory acts as a **Meta-Project** containing the "brain" or the "instructional layer" for the actual C++ project.

### Core Instructional Files
- **`MASTER_PROMPT.md`**: The primary architectural blueprint and persona definition (Turkish). It defines the "Senior C++ Architect" role and the mandatory repository structure.
- **`AGENTS.md`**: The mandatory **Execution Contract** for AI agents. It defines the step-by-step workflow: *Analyze → Impact → Plan → Implement → Integrate → Validate → Output*.
- **`prompt.md`**: A concise English summary of the project structure, core rules (isolation, warnings, build system), and AI behavioral mandates.
- **`prompt_deneme.md`**: An exhaustive, expert-level prompt (Turkish) detailing every technical requirement from CMake presets to versioning and documentation standards.

## Mandatory Project Architecture (Target State)
When implementing code, agents MUST adhere to this structure:
- `libs/`: Internal reusable libraries.
- `apps/`: Executable applications.
- `external/`: Third-party vendor code (Isolated via `SYSTEM`).
- `tests/`: GoogleTest-based unit and integration tests.
- `cmake/`: Shared modules and toolchains.
- `scripts/`: Automation and build helpers.
- `docs/`: Repository and project-level documentation.

## Core Mandates & Constraints

### 1. Technical Standards
- **CMake**: Minimum version 3.25. Use **target-based** configuration (no global flags).
- **External Isolation**: Never modify files in `external/`. Always use `add_subdirectory(... SYSTEM)` or `FetchContent(... SYSTEM)` to prevent vendor warnings from leaking into the build.
- **Quality Policy**: Strict warnings enabled for internal targets (`-Wall -Wextra -Wpedantic` etc.).
- **Build Presets**: `CMakePresets.json` is mandatory for GCC, Clang, and MSVC.
- **Versioning**: Integrated Git metadata accessible via runtime `--version` or `--buildinfo` flags.

### 2. Agent Behavioral Rules
- **Smallest Safe Change**: Prioritize build integrity and minimal impact.
- **Verification**: Always validate build integrity and preset compatibility after changes.
- **No Placeholders**: Output must be complete, working code with no `TODO` placeholders or partial implementations.
- **Target Creation Contract**: Every new target MUST include its own `CMakeLists.txt`, `README.md`, and `docs/` folder.

## Getting Started / Workflow
To continue building this project, use the **Execution Protocol** defined in `AGENTS.md`:
1.  **Analyze**: Identify which directory (`libs`, `apps`, etc.) is affected.
2.  **Impact**: Determine if a new target or CMake update is required.
3.  **Plan**: Select the minimal safe change.
4.  **Implement**: Write complete, production-grade code.
5.  **Integrate**: Update `CMakeLists.txt`, link dependencies, and add tests/docs.
6.  **Validate**: Run builds/tests to ensure zero regressions.
7.  **Output**: Deliver the final, working result.
