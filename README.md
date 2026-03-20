# Professional C++ CMake Project Template

[![CI](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml/badge.svg)](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CMake: 3.25+](https://img.shields.io/badge/CMake-3.25+-informational.svg)](https://cmake.org)

A production-ready, multi-target C++ boilerplate designed for high-performance applications. Whether you are building desktop apps or bare-metal embedded firmware, this template provides the infrastructure so you can focus on **logic**.

---

## 🎯 Why This Template?

| Feature | Description |
| :--- | :--- |
| **Modern CMake** | Target-based, clean, and modular architecture. |
| **Cross-Platform** | Seamless support for Linux, Windows (MSVC), and macOS. |
| **Embedded Ready** | Native support for ARM/GNU toolchains + automated `.bin`/`.hex`. |
| **Quality First** | Built-in Sanitizers (ASan/TSan), Static Analysis, and Coverage reports. |
| **DevOps Ready** | Automated GitHub CI, CPack for packaging, and VS Code GUI automation. |

---

## 🚀 Getting Started

### Prerequisites
- CMake 3.25+
- Ninja Build
- A C++ Compiler (GCC, Clang, or MSVC)

### Initialization (The "One-Time" Setup)
```bash
# 1. Clone the repo
git clone https://github.com/develooper1994/CppCmakeProjectTemplate.git
cd CppCmakeProjectTemplate

# 2. Rename the project to your app name
python3 scripts/init_project.py --name YourAppName

# 3. Enable Quality Hooks (Clang-Format, Lint, Secret Scan)
python3 scripts/setup_hooks.py
```

### The Terminal Build Flow
```bash
# 1. Build (Auto-detects environment)
python3 scripts/build.py

# 2. Run
./build/gcc-debug-static-x86_64/apps/main_app/main_app
```

---

## 🛠 Advanced Features

### Embedded & Custom Toolchains
Need to target custom hardware? Check the [Embedded Guide](docs/EMBEDDED.md) to integrate proprietary board SDKs or GNU toolchains in minutes.

### Static & Dynamic Linking
Switch easily between static and dynamic builds via:
```bash
cmake --preset gcc-debug-dynamic-x86_64
```

### Sanitizers & Analysis
Catch memory leaks and logic errors before they reach production:
```bash
cmake -DENABLE_ASAN=ON -DENABLE_CLANG_TIDY=ON .
```

---

## 🏛 Directory Structure
- `apps/` : Application entry points.
- `libs/` : Modüler, bağımsız derlenebilir kütüphaneler.
- `cmake/` : Proje yapı modülleri (Sanitizers, Coverage, Export).
- `scripts/` : Otomasyon (Build, Deploy, Init).
- `docs/` : Detaylı teknik rehberler.

---

## ⚖️ License
Licensed under the [MIT License](LICENSE).
