import os
import sys
from pathlib import Path

import pytest

# Ensure the `scripts` package is importable when running pytest from the repository root
sys.path.insert(0, os.path.abspath("scripts"))

from core.libpkg import create as create_mod


def test_create_library_rollback_on_write_error(tmp_path: Path, monkeypatch):
    root = tmp_path
    # prepare minimal cmake lists
    (root / "libs").mkdir()
    (root / "libs" / "CMakeLists.txt").write_text("# libs root\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "unit").mkdir(parents=True)
    (root / "tests" / "unit" / "CMakeLists.txt").write_text("# tests root\n", encoding="utf-8")

    original_write = Path.write_text

    def fake_write_text(self, data, encoding='utf-8', errors=None):
        # Simulate an IO error when writing the library source file
        if str(self).endswith(os.path.join('src', 'toy.cpp')):
            raise OSError("simulated write error")
        return original_write(self, data, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, 'write_text', fake_write_text)

    with pytest.raises(OSError):
        create_mod.create_library("toy", dry_run=False, root=root)

    # Ensure library dir was rolled back / not left behind
    assert not (root / "libs" / "toy").exists()
    # Ensure libs/CMakeLists.txt was not modified to include toy
    assert "toy" not in (root / "libs" / "CMakeLists.txt").read_text(encoding="utf-8")
