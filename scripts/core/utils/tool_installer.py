#!/usr/bin/env python3
"""
core/utils/tool_installer.py — Helper to detect and (optionally) install missing CLI tools.

This is intentionally small: it detects an executable on PATH and, when
`install_allowed` is True, attempts to install using a best-effort package
manager invocation (apt, brew, winget/choco). It logs progress via
`core.utils.common.Logger` and returns a boolean success indicator.
"""
from __future__ import annotations

import shutil
import subprocess
import platform
from typing import Iterable


from core.utils.common import Logger


def _choose_installer() -> str:
    system = platform.system()
    if system == "Linux":
        # prefer apt if available, otherwise try dnf/pacman
        if shutil.which("apt") or shutil.which("apt-get"):
            return "apt"
        if shutil.which("dnf"):
            return "dnf"
        if shutil.which("pacman"):
            return "pacman"
    if system == "Darwin":
        if shutil.which("brew"):
            return "brew"
    if system == "Windows":
        if shutil.which("winget"):
            return "winget"
        if shutil.which("choco"):
            return "choco"
    return "unknown"


def _format_install_cmd(installer: str, pkg: str) -> list[str]:
    if installer == "apt":
        return ["sudo", "apt", "update", "-y", "&&", "sudo", "apt", "install", "-y", pkg]
    if installer == "dnf":
        return ["sudo", "dnf", "install", "-y", pkg]
    if installer == "pacman":
        return ["sudo", "pacman", "-S", "--noconfirm", pkg]
    if installer == "brew":
        return ["brew", "install", pkg]
    if installer == "winget":
        return ["winget", "install", "--silent", pkg]
    if installer == "choco":
        return ["choco", "install", pkg, "-y"]
    # fallback to a conservative apt suggestion
    return ["sudo", "apt", "install", "-y", pkg]


def ensure_tool_available(name: str, pkg_candidates: Iterable[str] | None = None, *, install_allowed: bool = False) -> bool:
    """Return True if ``name`` is available on PATH, otherwise attempt to
    install from ``pkg_candidates`` when ``install_allowed`` is True.

    - ``name`` is the program/binary name to look for (e.g. 'clazy', 'scan-build').
    - ``pkg_candidates`` is an iterable of package names to try in order (platform package names).
    - ``install_allowed`` permits the helper to attempt installation using the detected package manager.

    The function logs progress and returns a boolean success/failure.
    """
    if shutil.which(name):
        Logger.debug(f"Tool found on PATH: {name}")
        return True

    if not install_allowed:
        Logger.debug(f"Tool {name} not found and installation not allowed")
        return False

    installer = _choose_installer()
    if installer == "unknown":
        Logger.error(f"No supported package manager found to install '{name}'. Please install it manually.")
        return False

    pkgs = list(pkg_candidates) if pkg_candidates else [name]
    for pkg in pkgs:
        cmd = _format_install_cmd(installer, pkg)
        Logger.info(f"Attempting to install '{name}' via package '{pkg}' using installer '{installer}'")
        Logger.info(f"Running: {' '.join(cmd)}")
        try:
            # Use shell for compound commands like apt update && apt install
            rc = subprocess.run(" ".join(cmd), shell=True).returncode
            if rc == 0:
                if shutil.which(name):
                    Logger.success(f"Successfully installed '{name}' (via {pkg}).")
                    return True
                else:
                    Logger.warn(f"Installer returned success but '{name}' still not on PATH.")
            else:
                Logger.warn(f"Installer returned non-zero ({rc}) for package '{pkg}'. Trying next candidate if any.")
        except Exception as e:
            Logger.error(f"Exception while trying to install '{pkg}': {e}")

    Logger.error(f"Failed to install any candidate package for '{name}'.")
    return False
