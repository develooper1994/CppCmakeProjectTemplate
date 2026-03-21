# Professional C++ CMake Project Template

[![CI](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml/badge.svg)](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CMake: 3.25+](https://img.shields.io/badge/CMake-3.25+-informational.svg)](https://cmake.org)
[![C++ Standard](https://img.shields.io/badge/C++-17-blue.svg)](https://isocpp.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20|%20Windows%20|%20macOS-lightgrey)](https://github.com/develooper1994/CppCmakeProjectTemplate)

A world-class, multi-target C++ project skeleton. Designed for high-performance applications with a focus on **Cross-Platform** compatibility, **Zero-Terminal** VS Code workflows, and **AI-Assisted** development.

---

## 🚀 Key Features

- **Cross-Platform**: Windows (MSVC), Linux (GCC/Clang), and macOS (AppleClang) support.
- **Modern CMake (3.25+)**: Pure target-based design. No global flags.
- **VS Code Optimized**: Full GUI integration (Build, Test, Debug, Deploy).
- **Dependency Management**: Vcpkg, Conan, and FetchContent integration.
- **Quality Guard**: GoogleTest, Sanitizers (ASan/TSan), Static Analysis, Coverage reports.
- **Embedded Ready**: ARM/GNU Toolchain support with auto-generated `.bin` & `.hex`.
- **Packaging**: CPack-ready (.deb, .zip, .tar.gz).

---

## 💻 Usage: The VS Code Way

1. **Select Preset**: Click **"CMake: [No Preset]"** in status bar.
2. **Build**: Press `F7` or click **Build**.
3. **Debug**: Press `F5` to debug `main_app`.
4. **Test**: Click **Test** in status bar to run GoogleTests.

## ⌨️ Usage: The Terminal Way

```bash
# 1. Build (Auto-detects environment)
python3 scripts/build.py

# 2. Run Application
./build/<preset-name>/apps/main_app/main_app

# 3. Clean Build
python3 scripts/clean.py
```

---

## 🔒 Quality Guards (Pre-Commit Hooks)

Before you commit, ensure your code is perfect:

```bash
python3 scripts/setup_hooks.py
```

*Checks: Clang-Format, Clang-Tidy, and Secret Scanner.*

---

## 🔄 Rename Project (Git Clone Sonrası)

VSCode extension yerine terminal kullanıyorsanız:

```bash
python3 scripts/init_project.py --name MyProject
```

Tüm dosyalardaki `CppCmakeProjectTemplate` referanslarını `MyProject` ile değiştirir.
LICENSE dosyası manuel güncellenmeli.

---

## 🧩 Library Management (libtool)

All library operations go through `scripts/libtool.py`.
In VS Code: `Ctrl+Shift+P` → **CppTemplate: Library Manager (libtool)**.

```bash
# Add a library
python3 scripts/libtool.py add my_lib
python3 scripts/libtool.py add renderer --deps core,math --link-app

# Remove (--delete also removes files)
python3 scripts/libtool.py remove my_lib --delete

# Rename (updates all source/CMake references)
python3 scripts/libtool.py rename old_name new_name

# Move (supports subdirectory layouts)
python3 scripts/libtool.py move renderer graphics/renderer

# Edit dependencies of an existing library
python3 scripts/libtool.py deps renderer --add math --remove old_dep

# Inspect
python3 scripts/libtool.py list
python3 scripts/libtool.py tree
python3 scripts/libtool.py doctor
```

Append `--dry-run` to any command to preview changes without applying them.

---

## 📁 Directory Structure

- `apps/` : Executable entry points.
- `libs/` : Modüler, bağımsız derlenebilir kütüphaneler.
- `cmake/` : Build system modules ([Embedded Tools](cmake/EmbeddedUtils.cmake)).
- `scripts/` : Otomasyon ([Project Init](scripts/init_project.py)).
- `docs/` : Detaylı teknik rehberler ([Embedded Guide](docs/EMBEDDED.md)).
- `.github/`: CI/CD workflows and AI Agent instructions.

---

## ⚖️ License

Licensed under the [MIT License](LICENSE).
