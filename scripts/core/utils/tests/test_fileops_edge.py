import sys
import os
import errno
from pathlib import Path

import pytest

# Make `scripts` importable
sys.path.insert(0, os.path.abspath("scripts"))

from core.utils.common import GlobalConfig
from core.utils.fileops import Transaction

GlobalConfig.JSON = True


def test_safe_rename_cross_device_rollback(tmp_path: Path, monkeypatch):
    root = tmp_path
    src = root / "old.txt"
    dst = root / "new.txt"
    src.write_text("orig", encoding="utf-8")

    orig_rename = Path.rename

    def fake_rename(self, target):
        # Simulate cross-device rename failure only for our src
        if str(self) == str(src):
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        return orig_rename(self, target)

    monkeypatch.setattr(Path, "rename", fake_rename)

    with pytest.raises(OSError):
        with Transaction(root=root) as txn:
            txn.safe_rename(src, dst)

    # Original file should still exist and be unchanged
    assert src.exists()
    assert src.read_text(encoding="utf-8") == "orig"


def test_safe_write_permission_error_rollback(tmp_path: Path, monkeypatch):
    root = tmp_path
    p = root / "file.txt"
    p.write_text("orig", encoding="utf-8")

    orig_write = Path.write_text

    def fake_write_text(self, data, encoding="utf-8", errors=None):
        # Simulate permission error when writing our file
        if str(self) == str(p):
            raise PermissionError("Permission denied")
        return orig_write(self, data, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "write_text", fake_write_text)

    with pytest.raises(PermissionError):
        with Transaction(root=root) as txn:
            txn.safe_write_text(p, "new")

    # Original content must be preserved after rollback
    assert p.exists()
    assert p.read_text(encoding="utf-8") == "orig"
