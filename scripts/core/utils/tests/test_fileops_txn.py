import sys
import os
from pathlib import Path

import pytest

# Ensure the `scripts` package is importable when running pytest from the repository root
sys.path.insert(0, os.path.abspath("scripts"))

from core.utils.common import GlobalConfig
from core.utils.fileops import Transaction

# Silence Logger to avoid writing to repository build_logs during tests
GlobalConfig.JSON = True


def test_safe_write_and_commit(tmp_path: Path):
    root = tmp_path
    p = root / "hello.txt"
    with Transaction(root=root) as txn:
        txn.safe_write_text(p, "hello")
        assert p.exists()
        assert p.read_text(encoding="utf-8") == "hello"

    # after commit the file remains; backup timestamp dir should be removed
    assert p.exists()
    assert p.read_text(encoding="utf-8") == "hello"
    backup_root = root / ".tool" / "fileops"
    if backup_root.exists():
        # parent may remain; ensure it's empty
        assert not any(backup_root.iterdir())


def test_modify_and_rollback(tmp_path: Path):
    root = tmp_path
    p = root / "file.txt"
    p.write_text("orig", encoding="utf-8")

    with pytest.raises(RuntimeError):
        with Transaction(root=root) as txn:
            txn.safe_write_text(p, "new")
            assert p.read_text(encoding="utf-8") == "new"
            raise RuntimeError("boom")

    # After rollback, original content is restored
    assert p.exists()
    assert p.read_text(encoding="utf-8") == "orig"
    backup_root = root / ".tool" / "fileops"
    if backup_root.exists():
        assert not any(backup_root.iterdir())


def test_safe_mkdir_and_rollback(tmp_path: Path):
    root = tmp_path
    d = root / "mydir"

    with pytest.raises(RuntimeError):
        with Transaction(root=root) as txn:
            txn.safe_mkdir(d)
            assert d.exists()
            raise RuntimeError("boom")

    assert not d.exists()
    backup_root = root / ".tool" / "fileops"
    if backup_root.exists():
        assert not any(backup_root.iterdir())


def test_safe_remove_and_rollback(tmp_path: Path):
    root = tmp_path
    dirp = root / "a"
    dirp.mkdir()
    p = dirp / "f.txt"
    p.write_text("data", encoding="utf-8")
    assert p.exists()

    with pytest.raises(RuntimeError):
        with Transaction(root=root) as txn:
            txn.safe_remove(p)
            assert not p.exists()
            raise RuntimeError("boom")

    # restored
    assert p.exists()
    assert p.read_text(encoding="utf-8") == "data"
    backup_root = root / ".tool" / "fileops"
    if backup_root.exists():
        assert not any(backup_root.iterdir())


def test_safe_rename_and_rollback(tmp_path: Path):
    root = tmp_path
    src = root / "old.txt"
    dst = root / "new.txt"
    src.write_text("orig", encoding="utf-8")

    with pytest.raises(RuntimeError):
        with Transaction(root=root) as txn:
            txn.safe_rename(src, dst)
            assert not src.exists()
            assert dst.exists()
            raise RuntimeError("oops")

    assert src.exists()
    assert src.read_text(encoding="utf-8") == "orig"
    assert not dst.exists()
    backup_root = root / ".tool" / "fileops"
    if backup_root.exists():
        assert not any(backup_root.iterdir())
