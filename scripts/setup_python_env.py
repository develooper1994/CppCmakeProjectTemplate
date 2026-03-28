#!/usr/bin/env python3
"""Cross-platform Python virtual environment creator.

Creates a venv on Linux, macOS and Windows and optionally installs
development requirements from `requirements-dev.txt`.

Usage:
  python3 scripts/setup_python_env.py --env .venv --install
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


def create_venv(env_dir: Path, python_exe: str | None = None) -> None:
    py = python_exe or sys.executable
    env_dir = env_dir.resolve()
    if env_dir.exists():
        print(f"Virtualenv already exists at {env_dir}")
        return
    run([py, "-m", "venv", str(env_dir)])
    print("Created venv at", env_dir)


def pip_in_venv(env_dir: Path) -> Path:
    if platform.system() == "Windows":
        return env_dir / "Scripts" / "pip.exe"
    return env_dir / "bin" / "pip"


def install_requirements(env_dir: Path, req_file: Path) -> None:
    pip = pip_in_venv(env_dir)
    if not pip.exists():
        raise FileNotFoundError(f"pip not found in venv: {pip}")
    run([str(pip), "install", "--upgrade", "pip", "wheel", "setuptools"])
    if req_file.exists():
        run([str(pip), "install", "-r", str(req_file)])
    else:
        print("No requirements-dev.txt found; skipping package install")


def print_activation(env_dir: Path) -> None:
    if platform.system() == "Windows":
        print(f"To activate (PowerShell): {env_dir}\\Scripts\\Activate.ps1")
        print(f"To activate (cmd): {env_dir}\\Scripts\\activate.bat")
    else:
        print(f"To activate: source {env_dir}/bin/activate")


def main() -> None:
    p = argparse.ArgumentParser(description="Create project Python virtual environment")
    p.add_argument("--env", default=".venv", help="Directory to create the virtualenv in")
    p.add_argument("--python", default=None, help="Python executable to use (default: current Python)")
    p.add_argument("--install", action="store_true", help="Install requirements-dev.txt into venv")
    args = p.parse_args()

    env_dir = Path(args.env)
    create_venv(env_dir, args.python)
    if args.install:
        install_requirements(env_dir, Path("requirements-dev.txt"))
    print_activation(env_dir)


if __name__ == "__main__":
    main()
