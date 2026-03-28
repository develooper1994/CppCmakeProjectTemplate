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
import shutil
import venv
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


def _env_python(env_dir: Path) -> Path:
    if platform.system() == "Windows":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def create_venv(env_dir: Path, python_exe: str | None = None, recreate: bool = False) -> Path:
    """Create a virtual environment and return path to its Python executable.

    - If `python_exe` is provided, uses that interpreter to run `-m venv`.
    - Otherwise uses the current interpreter's venv builder.
    - If `recreate` is True, removes any existing env first.
    """
    env_dir = env_dir.resolve()
    if env_dir.exists():
        if recreate:
            print(f"Removing existing venv at {env_dir}")
            shutil.rmtree(env_dir)
        else:
            print(f"Virtualenv already exists at {env_dir}")
            return _env_python(env_dir)

    if python_exe:
        _run([python_exe, "-m", "venv", str(env_dir)])
    else:
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(str(env_dir))

    py = _env_python(env_dir)
    if not py.exists():
        raise FileNotFoundError(f"Python not found in created venv: {py}")

    # Ensure pip is available and up-to-date
    try:
        _run([str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"])
    except Exception:
        # Last resort: try ensurepip
        try:
            _run([str(py), "-m", "ensurepip", "--upgrade"])
        except Exception:
            print("Warning: could not bootstrap pip in venv; proceed without pip")

    print("Created venv at", env_dir)
    return py


def install_requirements(py_exe: Path, req_file: Path) -> None:
    if not req_file.exists():
        print("No requirements-dev.txt found; skipping package install")
        return
    _run([str(py_exe), "-m", "pip", "install", "-r", str(req_file)])


def print_activation(env_dir: Path) -> None:
    if platform.system() == "Windows":
        print(f"To activate (PowerShell): {env_dir / 'Scripts' / 'Activate.ps1'}")
        print(f"To activate (cmd): {env_dir / 'Scripts' / 'activate.bat'}")
    else:
        print(f"To activate: source {env_dir / 'bin' / 'activate'}")


def main() -> None:
    p = argparse.ArgumentParser(description="Create project Python virtual environment")
    p.add_argument("--env", default=".venv", help="Directory to create the virtualenv in")
    p.add_argument("--python", default=None, help="Python executable to use (default: current Python)")
    p.add_argument("--install", action="store_true", help="Install requirements-dev.txt into venv")
    p.add_argument("--recreate", action="store_true", help="Recreate the virtualenv if it exists")
    args = p.parse_args()

    env_dir = Path(args.env)
    py = create_venv(env_dir, args.python, recreate=args.recreate)
    if args.install:
        install_requirements(py, Path("requirements-dev.txt"))
    print_activation(env_dir)


if __name__ == "__main__":
    main()
