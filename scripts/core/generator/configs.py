"""
core/generator/configs.py — Metadata-aware project config generation.

Generates or tracks project configuration files such as:
  - LICENSE and pyproject.toml (rendered from ProjectContext)
  - Git configs: .gitignore, .editorconfig, .clang-format, etc.
  - Docker and VS Code configs (gated by generation profile)
  - Extension package metadata for the full profile
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

from core.utils.common import Logger

if __name__ != "__main__":
    from core.generator.engine import ProjectContext, is_feature_enabled

# Root-level config files copied as-is
ROOT_CONFIGS = [
    ".clang-format",
    ".clang-tidy",
    ".clangd",
    ".cmake-format",
    ".cppcheck-suppressions.txt",
    ".dockerignore",
    ".editorconfig",
    ".gitignore",
]


def _find_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "tool.toml").exists():
            return parent
    raise FileNotFoundError("Cannot find project root")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "cpp-project").lower()).strip("-")
    return slug or "cpp-project"


def _copyright_line(author: str) -> str:
    year = datetime.now().year
    return f"Copyright (c) {year}{(' ' + author) if author else ''}".rstrip()


def _gen_license(ctx: ProjectContext) -> str:
    license_id = str(ctx.license or "MIT").strip() or "MIT"
    author = (ctx.author or "").strip()
    copyright_line = _copyright_line(author)

    templates: dict[str, str] = {
        "MIT": f"""MIT License

{copyright_line}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""",
        "Apache-2.0": f"""Apache License
Version 2.0, January 2004
https://www.apache.org/licenses/

{copyright_line}

Licensed under the Apache License, Version 2.0 (the \"License\");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an \"AS IS\" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
""",
        "BSD-3-Clause": f"""BSD 3-Clause License

{copyright_line}

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS \"AS IS\".
""",
        "MPL-2.0": f"""Mozilla Public License Version 2.0

{copyright_line}

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
""",
        "GPL-3.0-only": f"""GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

{copyright_line}

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 only.
""",
        "LGPL-3.0-only": f"""GNU LESSER GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

{copyright_line}

This library is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, version 3 only.
""",
        "Unlicense": f"""This is free and unencumbered software released into the public domain.

{copyright_line}

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.
""",
    }

    if not author:
        Logger.warn("Generating LICENSE without author name; set --author or git config user.name to fill it in.")

    if license_id not in templates:
        Logger.warn(f"Unsupported license '{license_id}'; generating a placeholder SPDX notice instead.")
        return f"SPDX-License-Identifier: {license_id}\n\n{copyright_line}\n"

    return templates[license_id]


def _gen_pyproject(ctx: ProjectContext) -> str:
    slug = _slugify(ctx.name)
    # Use explicit pyproject_name from tool.toml if set, else derive from slug
    pyproject_name = getattr(ctx, "pyproject_name", "") or f"{slug}-tool"
    authors = f'authors = [\n  {{ name = "{ctx.author}" }}\n]\n' if ctx.author else "authors = []\n"
    license_id = str(ctx.license or "MIT").strip() or "MIT"
    homepage = getattr(ctx, "homepage", "") or ""

    # URLs section
    urls_section = ""
    if homepage:
        urls_section = f'''
[project.urls]
Homepage = "{homepage}"
Repository = "{homepage}"
Documentation = "{homepage}/tree/main/docs"
Issues = "{homepage}/issues"
'''

    return f'''[tool.ruff]
line-length = 88
target-version = "py311"
# Ignore imports-not-at-top pattern used by scripts that modify sys.path at runtime
ignore = ["E402"]

# Exclude common build / virtualenv / cache directories
exclude = [
  "build",
  "build/**",
  ".venv",
  ".venv/**",
  "build_logs",
  "build_logs/**",
  "extension/*.vsix",
  "__pycache__",
  "**/__pycache__",
]

[tool.ruff.per-file-ignores]
# Allow some TUI files or generated code to keep imports flexible
"scripts/tui/*" = ["E402"]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{pyproject_name}"
version = "{ctx.version}"
description = "Professional C++ CMake project scaffolding and automation CLI"
readme = "README.md"
license = "{license_id}"
requires-python = ">=3.10"
{authors}keywords = ["cpp", "cmake", "scaffolding", "project-template", "build-automation", "code-generator"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: C++",
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Code Generators",
]
dependencies = [
  "Jinja2>=3.1",
  "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1",
    "build>=1.0",
    "twine>=4.0",
]
tui = [
    "textual>=0.40",
]
{urls_section}
[project.scripts]
{pyproject_name} = "tool:main"

[tool.pytest.ini_options]
pythonpath = ["scripts"]
testpaths = [
    "scripts/tests",
    "scripts/core/commands/tests",
    "scripts/core/libpkg/tests",
    "scripts/core/utils/tests",
    "scripts/core/generator/tests",
]
norecursedirs = ["extension/templates", "build", ".venv", "__pycache__", "tui"]
# Disable system-level plugins that break headless / CI environments
addopts = "-p no:qt -p no:xvfb -p no:recording -p no:vcr"

[tool.setuptools]
py-modules = ["tool", "tui"]

[tool.setuptools.packages.find]
where = ["scripts"]
exclude = ["tests", "tests.*", "*.tests", "*.tests.*"]

[tool.setuptools.package-dir]
"" = "scripts"

[tool.setuptools.package-data]
"core.libpkg" = ["templates/*.jinja2"]
'''


def _is_full_profile(ctx: ProjectContext) -> bool:
    return str(getattr(ctx, "profile", "full") or "full").strip().lower() == "full"


def _gen_flake_nix(ctx: ProjectContext) -> str:
    """Generate a Nix flake for reproducible development environments."""
    name = ctx.name or "CppProject"
    description = ctx.description or f"{name} — C++ project"
    cxx_std = ctx.cxx_standard or "17"

    return f'''{{
  description = "{description}";

  inputs = {{
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  }};

  outputs = {{ self, nixpkgs, flake-utils }}:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${{system}};
      in {{
        devShells.default = pkgs.mkShell {{
          name = "{name}-dev";

          packages = with pkgs; [
            # Build tools
            cmake
            ninja
            gnumake
            pkg-config

            # Compilers
            gcc
            clang

            # C++ tooling
            clang-tools          # clang-tidy, clang-format
            ccache
            gdb
            valgrind

            # Testing
            gtest

            # Python (for tool.py)
            python3
            python3Packages.pip
            python3Packages.pytest

            # Documentation
            doxygen
          ];

          shellHook = \'\'
            echo "🔧 {name} dev environment (Nix)"
            echo "   C++ standard: {cxx_std}"
            echo "   Run: python3 scripts/tool.py build"
          \'\';

          # Environment variables
          CMAKE_GENERATOR = "Ninja";
        }};

        packages.default = pkgs.stdenv.mkDerivation {{
          pname = "{name}";
          version = "{ctx.version or "0.0.0"}";
          src = ./.;

          nativeBuildInputs = with pkgs; [ cmake ninja pkg-config ];
          buildInputs = with pkgs; [ gtest ];

          cmakeFlags = [
            "-DCMAKE_CXX_STANDARD={cxx_std}"
          ];

          meta = with pkgs.lib; {{
            description = "{description}";
            license = licenses.{_nix_license(ctx.license)};
          }};
        }};
      }});
}}
'''


def _nix_license(license_id: str) -> str:
    """Map SPDX license identifier to Nix license attribute name."""
    mapping = {
        "MIT": "mit",
        "Apache-2.0": "asl20",
        "GPL-2.0": "gpl2Only",
        "GPL-3.0": "gpl3Only",
        "LGPL-2.1": "lgpl21",
        "LGPL-3.0": "lgpl3",
        "BSD-2-Clause": "bsd2",
        "BSD-3-Clause": "bsd3",
        "MPL-2.0": "mpl20",
        "Unlicense": "unlicense",
        "ISC": "isc",
        "Zlib": "zlib",
    }
    return mapping.get(license_id, "mit")


def _gen_devcontainer(ctx: ProjectContext) -> str:
    """Generate .devcontainer/devcontainer.json."""
    import json

    name = ctx.name or "CppProject"

    extensions = [
        "ms-vscode.cpptools",
        "ms-vscode.cmake-tools",
        "twxs.cmake",
        "ms-vscode.cpptools-extension-pack",
        "GitHub.copilot",
    ]

    devcontainer: dict[str, Any] = {
        "name": name,
        "image": "mcr.microsoft.com/devcontainers/cpp:1-ubuntu-24.04",
        "features": {
            "ghcr.io/devcontainers/features/cmake:1": {
                "version": ctx.cmake_minimum or "3.25",
            },
            "ghcr.io/devcontainers/features/python:1": {
                "version": "3.12",
            },
        },
        "customizations": {
            "vscode": {
                "extensions": extensions,
                "settings": {
                    "cmake.configureOnOpen": True,
                    "cmake.buildDirectory": "${workspaceFolder}/build/${buildKitVendor}-${buildType}",
                },
            }
        },
        "postCreateCommand": "python3 scripts/tool.py setup --install || true",
        "remoteUser": "vscode",
    }

    return json.dumps(devcontainer, indent=2) + "\n"


def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    root = _find_project_root()
    files: dict[str, str] = {
        "LICENSE": _gen_license(ctx),
        "pyproject.toml": _gen_pyproject(ctx),
    }

    # Root config files
    for fname in ROOT_CONFIGS:
        fpath = root / fname
        if fpath.is_file():
            try:
                files[fname] = fpath.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                pass  # skip binary files

    include_docker = is_feature_enabled(ctx, "docker", default=_is_full_profile(ctx))
    include_vscode = is_feature_enabled(ctx, "vscode", default=_is_full_profile(ctx) and ctx.vscode.get("generate", True))
    include_extension = is_feature_enabled(ctx, "extension", default=_is_full_profile(ctx) and ctx.extension.get("generate", True))

    if include_docker:
        docker_dir = root / "docker"
        if docker_dir.is_dir():
            for df in sorted(docker_dir.iterdir()):
                if df.is_file() and df.name.startswith("Dockerfile"):
                    files[f"docker/{df.name}"] = df.read_text(encoding="utf-8")

    if include_vscode:
        vscode_dir = root / ".vscode"
        if vscode_dir.is_dir() and ctx.vscode.get("generate", True):
            for vf in sorted(vscode_dir.iterdir()):
                if vf.is_file() and vf.suffix == ".json":
                    files[f".vscode/{vf.name}"] = vf.read_text(encoding="utf-8")

    if include_extension:
        ext_dir = root / "extension"
        if ext_dir.is_dir() and ctx.extension.get("generate", True):
            for ef_name in ("package.json",):
                ef = ext_dir / ef_name
                if ef.is_file():
                    files[f"extension/{ef_name}"] = ef.read_text(encoding="utf-8")

    # DevContainer
    if is_feature_enabled(ctx, "devcontainer", default=_is_full_profile(ctx)):
        files[".devcontainer/devcontainer.json"] = _gen_devcontainer(ctx)

    # Nix Flake
    if is_feature_enabled(ctx, "nix", default=False):
        files["flake.nix"] = _gen_flake_nix(ctx)

    return files
