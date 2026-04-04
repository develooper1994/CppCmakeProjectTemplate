"""
core/generator/manifest.py — Hash-based generation manifest tracking.

Tracks every generated file's content hash so that subsequent regenerations
can detect user modifications and decide whether to overwrite, skip, or merge.

Manifest format (.tool/generation_manifest.json):
{
  "version": 1,
  "files": {
    "CMakeLists.txt": {
      "hash": "<sha256>",
      "generated_at": "<ISO-8601>",
      "component": "root-cmake"
    },
    ...
  }
}
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GenerationManifest:
    """Track generated file hashes for intelligent regeneration."""

    VERSION = 1

    def __init__(self, manifest_path: Path):
        self._path = manifest_path
        self._data: dict[str, Any] = {
            "version": self.VERSION,
            "files": {},
            "component_hashes": {},
        }
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and raw.get("version") == self.VERSION:
                    self._data = raw
                    # Ensure component_hashes key exists for older manifests
                    self._data.setdefault("component_hashes", {})
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def hash_content(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_entry(self, rel_path: str) -> dict[str, str] | None:
        return self._data["files"].get(rel_path)

    def record(self, rel_path: str, content: str, component: str) -> None:
        self._data["files"][rel_path] = {
            "hash": self.hash_content(content),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "component": component,
        }

    def is_unchanged(self, rel_path: str, current_content: str) -> bool:
        """Check if file on disk matches the last generated hash."""
        entry = self.get_entry(rel_path)
        if entry is None:
            return False
        return entry["hash"] == self.hash_content(current_content)

    def is_stale(self, rel_path: str, new_content: str) -> bool:
        """Check if the new generated content differs from what was last written."""
        entry = self.get_entry(rel_path)
        if entry is None:
            return True
        return entry["hash"] != self.hash_content(new_content)

    def file_was_modified_by_user(
        self, rel_path: str, disk_content: str
    ) -> bool:
        """True if the file on disk differs from what the generator last wrote."""
        entry = self.get_entry(rel_path)
        if entry is None:
            return False  # never generated → not "modified by user"
        return entry["hash"] != self.hash_content(disk_content)

    def list_files(self, component: str | None = None) -> list[str]:
        files = self._data["files"]
        if component is None:
            return list(files.keys())
        return [k for k, v in files.items() if v.get("component") == component]

    def remove(self, rel_path: str) -> None:
        self._data["files"].pop(rel_path, None)

    # -- Component-level input hashing for incremental generation ----------

    def get_component_hash(self, component: str) -> str | None:
        """Return the stored input hash for a component, or None."""
        return self._data["component_hashes"].get(component)

    def set_component_hash(self, component: str, input_hash: str) -> None:
        """Store the input hash for a component."""
        self._data["component_hashes"][component] = input_hash

    def is_component_unchanged(self, component: str, input_hash: str) -> bool:
        """True if the component's stored input hash matches *input_hash*."""
        stored = self.get_component_hash(component)
        return stored is not None and stored == input_hash
