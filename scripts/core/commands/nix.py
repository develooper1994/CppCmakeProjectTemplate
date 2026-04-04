"""
core/commands/nix.py — Nix flake.nix generation
=================================================

Generates a flake.nix for reproducible development environments
with hermetic toolchain pinning.

Usage:
  tool nix generate [--output DIR]
  tool nix generate --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.utils.common import Logger, CLIResult, PROJECT_ROOT, get_project_name, get_project_version

COMMAND_META = {
    "name": "nix",
    "description": "Generate Nix flake for reproducible dev environments",
}


def _generate_flake_nix(name: str, version: str, cxx_std: str = "17") -> str:
    """Generate flake.nix content."""
    return f'''{{
  description = "{name} — C++ CMake project";

  inputs = {{
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  }};

  outputs = {{ self, nixpkgs, flake-utils }}:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {{ inherit system; }};
      in
      {{
        devShells.default = pkgs.mkShell {{
          name = "{name}-dev";

          packages = with pkgs; [
            # Build tools
            cmake
            ninja
            pkg-config

            # Compilers
            gcc
            clang

            # C++ dependencies (add project-specific deps here)
            gtest

            # Development tools
            ccache
            clang-tools        # clang-tidy, clang-format
            cppcheck
            valgrind
            gdb
            lcov

            # Python (for tool.py)
            python3
            python3Packages.pip
          ];

          shellHook = \'\'
            echo "🔧 {name} development environment (Nix)"
            echo "   CMake: $(cmake --version | head -1)"
            echo "   GCC:   $(gcc --version | head -1)"
            echo "   Clang: $(clang --version | head -1)"
            echo ""
            echo "   Build: python3 scripts/tool.py build"
            echo "   Test:  python3 scripts/tool.py build check --no-sync"
          \'\';

          # C++ standard for LSP / IDE integration
          CMAKE_EXPORT_COMPILE_COMMANDS = "ON";
        }};

        packages.default = pkgs.stdenv.mkDerivation {{
          pname = "{name}";
          version = "{version}";
          src = ./.;

          nativeBuildInputs = with pkgs; [ cmake ninja pkg-config ];
          buildInputs = with pkgs; [ gtest ];

          cmakeFlags = [
            "-DCMAKE_CXX_STANDARD={cxx_std}"
            "-DCMAKE_BUILD_TYPE=Release"
          ];
        }};
      }});
}}
'''


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="tool nix",
        description="Generate Nix flake.nix for reproducible dev environments",
    )
    sub = parser.add_subparsers(dest="subcommand")
    gen = sub.add_parser("generate", help="Generate flake.nix")
    gen.add_argument("--output", "-o", default=None, help="Output directory (default: project root)")
    gen.add_argument("--dry-run", action="store_true", help="Print without writing")

    args = parser.parse_args(argv)
    if not args.subcommand:
        args.subcommand = "generate"

    name = get_project_name()
    version = get_project_version()

    content = _generate_flake_nix(name, version)

    if getattr(args, "dry_run", False):
        print(content)
        return

    out_dir = Path(args.output) if getattr(args, "output", None) else PROJECT_ROOT
    flake_path = out_dir / "flake.nix"
    flake_path.write_text(content, encoding="utf-8")
    Logger.success(f"Generated {flake_path}")

    # Also generate .envrc for direnv integration
    envrc = out_dir / ".envrc"
    if not envrc.exists():
        envrc.write_text("use flake\n", encoding="utf-8")
        Logger.success(f"Generated {envrc} (direnv integration)")
