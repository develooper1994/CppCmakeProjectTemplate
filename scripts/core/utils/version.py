"""Version helpers for the repository.

Provides a small `Version` dataclass that understands versions of the
form: <major>.<middle>.<minor>+<revision>

Examples:
  1.2.3+45
  1.0.5

Revision is optional. The 'base' version is the three-part numeric
version (major.middle.minor) and is used where build systems do not
accept build metadata (CMake, npm package.json, etc.).

This module is intentionally lightweight and avoids importing other
project modules to keep imports simple.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Optional


VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\+(\d+))?$")


@dataclass
class Version:
    major: int
    middle: int
    minor: int
    revision: Optional[int] = None

    @classmethod
    def parse(cls, s: str) -> "Version":
        s = s.strip()
        m = VERSION_RE.match(s)
        if not m:
            raise ValueError(f"Invalid version: {s}")
        maj, mid, mino, rev = m.groups()
        return cls(int(maj), int(mid), int(mino), int(rev) if rev is not None else None)

    def base(self) -> str:
        return f"{self.major}.{self.middle}.{self.minor}"

    def __str__(self) -> str:
        if self.revision is None:
            return self.base()
        return f"{self.base()}+{self.revision}"

    def bump_major(self) -> "Version":
        return Version(self.major + 1, 0, 0, 0)

    def bump_middle(self) -> "Version":
        return Version(self.major, self.middle + 1, 0, 0)

    def bump_minor(self) -> "Version":
        return Version(self.major, self.middle, self.minor + 1, 0)

    def set_revision(self, rev: int) -> "Version":
        return Version(self.major, self.middle, self.minor, rev)


def read_version_file(path: Path) -> Version:
    if not path.exists():
        # try to fall back to git count if available
        try:
            out = subprocess.run(["git", "rev-list", "--count", "HEAD"], check=True, stdout=subprocess.PIPE, text=True)
            rev = int(out.stdout.strip())
        except Exception:
            rev = 0
        # default base version
        return Version(1, 0, 0, rev)
    text = path.read_text(encoding="utf-8").strip()
    return Version.parse(text)


def write_version_file(path: Path, v: Version) -> None:
    path.write_text(str(v) + "\n", encoding="utf-8")


def guess_revision_from_git() -> int:
    try:
        out = subprocess.run(["git", "rev-list", "--count", "HEAD"], check=True, stdout=subprocess.PIPE, text=True)
        return int(out.stdout.strip())
    except Exception:
        return 0
