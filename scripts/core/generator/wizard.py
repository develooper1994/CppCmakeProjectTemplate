"""
core/generator/wizard.py — Interactive project creation wizard.

Provides a step-by-step prompt-driven flow for ``tool generate --interactive``
and ``tool init``.  Also usable non-interactively with sensible defaults so
that scripts and CI can call ``Wizard(interactive=False).run()``.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PROFILES = ("full", "minimal", "library", "app", "embedded")
VALID_STANDARDS = ("11", "14", "17", "20", "23")
VALID_LICENSES = (
    "MIT", "Apache-2.0", "BSD-3-Clause", "MPL-2.0",
    "GPL-3.0-only", "LGPL-3.0-only", "Unlicense",
)
TOGGLEABLE_FEATURES = ("ci", "docker", "vscode", "extension", "docs", "fuzz")


# ---------------------------------------------------------------------------
# Answers dataclass
# ---------------------------------------------------------------------------

@dataclass
class WizardAnswers:
    """Collected answers from the interactive wizard."""

    name: str = "MyProject"
    description: str = ""
    author: str = ""
    contact: str = ""
    license: str = "MIT"
    cxx_standard: str = "17"
    profile: str = "full"
    libs: list[str] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)
    features_without: list[str] = field(default_factory=list)

    def to_config(self) -> dict[str, Any]:
        """Convert wizard answers into a tool.toml-style config dict."""
        lib_defs = [
            {"name": name, "type": "normal", "deps": []}
            for name in self.libs
        ]
        app_defs = []
        for app_name in self.apps:
            deps = list(self.libs)  # default: link all libs
            app_defs.append({"name": app_name, "deps": deps, "gui": False})

        cfg: dict[str, Any] = {
            "project": {
                "name": self.name,
                "version": "0.1.0",
                "description": self.description,
                "author": self.author,
                "contact": self.contact,
                "license": self.license,
                "cxx_standard": self.cxx_standard,
                "cmake_minimum": "3.25",
                "libs": lib_defs,
                "apps": app_defs,
                "tests": {
                    "framework": "gtest",
                    "fuzz": False,
                    "auto_generate": True,
                },
            },
            "cmake_modules": {
                "enabled": [
                    "CxxStandard", "ProjectConfigs", "ProjectOptions",
                    "BuildInfo", "Sanitizers", "Hardening", "FeatureFlags",
                    "LTO", "BuildCache",
                ],
            },
            "ci": {},
            "deps": {},
            "docker": {},
            "vscode": {},
            "git": {"init": "auto"},
            "docs": {},
            "extension": {},
            "generate": {
                "profile": self.profile,
                "on_conflict": "overwrite",
            },
            "build": {},
            "presets": {},
            "security": {},
            "hooks": {},
            "embedded": {},
            "gpu": {},
        }

        if self.features_without:
            cfg["generate"]["without"] = list(self.features_without)

        return cfg


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _read_git_config(key: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "config", key],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False,
        )
    except FileNotFoundError:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _prompt(label: str, default: str = "") -> str:
    """Prompt the user for a single-line value."""
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"  {label}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)
    return raw or default


def _prompt_choice(label: str, options: tuple[str, ...], default: str) -> str:
    """Prompt the user to pick from a list of options."""
    options_str = " / ".join(
        f"[{o}]" if o == default else o for o in options
    )
    while True:
        raw = _prompt(f"{label} ({options_str})", default)
        if raw in options:
            return raw
        print(f"    Invalid choice. Pick one of: {', '.join(options)}")


def _prompt_list(label: str, hint: str = "comma-separated") -> list[str]:
    """Prompt the user for a comma-separated list of names."""
    raw = _prompt(f"{label} ({hint})", "")
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _prompt_yes_no(label: str, default: bool = True) -> bool:
    """Prompt the user for a yes/no answer."""
    suffix = "[Y/n]" if default else "[y/N]"
    raw = _prompt(f"{label} {suffix}", "y" if default else "n").lower()
    return raw in ("y", "yes", "1", "true")


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

class Wizard:
    """Interactive (or non-interactive) project creation wizard."""

    def __init__(self, *, interactive: bool = True) -> None:
        self._interactive = interactive

    def run(self) -> WizardAnswers:
        if not self._interactive:
            return self._defaults()
        return self._interactive_flow()

    # -- non-interactive defaults -------------------------------------------

    @staticmethod
    def _defaults() -> WizardAnswers:
        return WizardAnswers(
            name="MyProject",
            author=_read_git_config("user.name"),
            contact=_read_git_config("user.email"),
        )

    # -- interactive flow ---------------------------------------------------

    def _interactive_flow(self) -> WizardAnswers:
        print()
        print("  ── CppCmakeProjectTemplate — Project Wizard ──")
        print()

        name = _prompt("Project name", "MyProject")
        description = _prompt("Short description", "")
        author = _prompt("Author", _read_git_config("user.name"))
        contact = _prompt("Contact email", _read_git_config("user.email"))

        print()
        license_id = _prompt_choice("License", VALID_LICENSES, "MIT")
        cxx_standard = _prompt_choice("C++ standard", VALID_STANDARDS, "17")
        profile = _prompt_choice("Profile", VALID_PROFILES, "full")

        print()
        libs = _prompt_list("Libraries to create", "comma-separated, e.g. core,utils")
        apps: list[str] = []
        if profile != "library":
            apps = _prompt_list("Applications to create", "comma-separated, e.g. main_app,cli")

        # Feature toggles
        print()
        without: list[str] = []
        for feat in TOGGLEABLE_FEATURES:
            default_on = feat not in _profile_disabled_features(profile)
            if default_on:
                if not _prompt_yes_no(f"Enable {feat}?", default=True):
                    without.append(feat)
            else:
                if not _prompt_yes_no(f"Enable {feat}?", default=False):
                    without.append(feat)

        print()
        return WizardAnswers(
            name=name,
            description=description,
            author=author,
            contact=contact,
            license=license_id,
            cxx_standard=cxx_standard,
            profile=profile,
            libs=libs,
            apps=apps,
            features_without=without,
        )


def _profile_disabled_features(profile: str) -> set[str]:
    """Return the set of features disabled by default for a profile."""
    from core.generator.engine import PROFILE_DEFAULT_FEATURES
    return PROFILE_DEFAULT_FEATURES.get(profile, set())
