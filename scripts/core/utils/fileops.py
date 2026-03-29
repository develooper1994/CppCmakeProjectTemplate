from __future__ import annotations

import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.utils.common import PROJECT_ROOT, Logger


class TransactionError(Exception):
    pass


class Transaction:
    """Simple transactional file operations helper.

    Usage:
        with Transaction() as txn:
            txn.safe_mkdir(path)
            txn.safe_write_text(file, text)
            txn.safe_remove(old)
        # On exception: changes are rolled back automatically.
    """

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root is not None else PROJECT_ROOT
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        self.backup_dir = self.root / ".tool" / "fileops" / ts
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._ops: List[Dict[str, Any]] = []
        self._backed: set[str] = set()
        self._committed = False

    # --- internal helpers -------------------------------------------------
    def _abs(self, p: Path) -> Path:
        return p if p.is_absolute() else (self.root / p)

    def _rel(self, p: Path) -> Path:
        try:
            return p.resolve().relative_to(self.root.resolve())
        except Exception:
            return Path(p.name)

    def _backup(self, p: Path) -> Optional[Path]:
        p = self._abs(p)
        if not p.exists():
            return None
        key = str(p.resolve())
        if key in self._backed:
            return self.backup_dir / self._rel(p)
        dest = self.backup_dir / self._rel(p)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            if p.is_dir():
                shutil.copytree(p, dest)
            else:
                shutil.copy2(p, dest)
            self._backed.add(key)
            return dest
        except Exception as e:
            Logger.error(f"Backup failed for {p}: {e}")
            raise TransactionError(e)

    # --- public safe operations -------------------------------------------
    def safe_mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        p = self._abs(path)
        if not p.exists():
            p.mkdir(parents=parents, exist_ok=exist_ok)
            self._ops.append({"op": "created_dir", "path": str(p)})

    def safe_write_text(self, path: Path, text: str, encoding: str = "utf-8") -> None:
        p = self._abs(path)
        if p.exists():
            bak = self._backup(p)
            self._ops.append({"op": "modified", "path": str(p), "backup": str(bak) if bak else None})
        else:
            # ensure parent exists
            if not p.parent.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                self._ops.append({"op": "created_dir", "path": str(p.parent)})
            self._ops.append({"op": "created", "path": str(p)})
        p.write_text(text, encoding=encoding)

    def safe_write_bytes(self, path: Path, data: bytes) -> None:
        p = self._abs(path)
        if p.exists():
            bak = self._backup(p)
            self._ops.append({"op": "modified", "path": str(p), "backup": str(bak) if bak else None})
        else:
            if not p.parent.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                self._ops.append({"op": "created_dir", "path": str(p.parent)})
            self._ops.append({"op": "created", "path": str(p)})
        p.write_bytes(data)

    def safe_remove(self, path: Path) -> None:
        p = self._abs(path)
        if not p.exists():
            return
        bak = self._backup(p)
        self._ops.append({"op": "deleted", "path": str(p), "backup": str(bak) if bak else None})
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()

    def safe_rename(self, src: Path, dst: Path) -> None:
        s = self._abs(src)
        d = self._abs(dst)
        if not s.exists():
            raise FileNotFoundError(s)
        bak = self._backup(s)
        # record rename so we can reverse it
        self._ops.append({"op": "renamed", "src": str(s), "dst": str(d), "backup": str(bak) if bak else None})
        d.parent.mkdir(parents=True, exist_ok=True)
        s.rename(d)

    # --- commit / rollback -----------------------------------------------
    def commit(self) -> None:
        try:
            # remove backups
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
        except Exception as e:
            Logger.warn(f"Failed to remove backup dir {self.backup_dir}: {e}")
        self._committed = True

    def rollback(self) -> None:
        Logger.warn("Transaction rollback: restoring backups")
        # reverse operations
        for op in reversed(self._ops):
            try:
                if op["op"] == "created":
                    p = Path(op["path"])
                    if p.exists():
                        if p.is_dir():
                            shutil.rmtree(p)
                        else:
                            p.unlink()
                elif op["op"] == "created_dir":
                    p = Path(op["path"])
                    # remove directory created during transaction; use rmtree to ensure cleanup
                    try:
                        if p.exists():
                            shutil.rmtree(p)
                    except Exception:
                        pass
                elif op["op"] in ("modified", "deleted"):
                    p = Path(op["path"])
                    bak = Path(op.get("backup")) if op.get("backup") else None
                    if bak and bak.exists():
                        # restore
                        if p.exists():
                            if p.is_dir():
                                shutil.rmtree(p)
                            else:
                                p.unlink()
                        # move back
                        bak_parent = p.parent
                        bak_parent.mkdir(parents=True, exist_ok=True)
                        bak.rename(p)
                elif op["op"] == "renamed":
                    src = Path(op["src"])
                    dst = Path(op["dst"])
                    # if dst exists, attempt to move back
                    if dst.exists():
                        # ensure src parent
                        src.parent.mkdir(parents=True, exist_ok=True)
                        dst.rename(src)
                    else:
                        # try restore from backup
                        bak = Path(op.get("backup")) if op.get("backup") else None
                        if bak and bak.exists():
                            bak_parent = src.parent
                            bak_parent.mkdir(parents=True, exist_ok=True)
                            bak.rename(src)
            except Exception as e:
                Logger.error(f"Rollback step failed for op {op}: {e}")

        # cleanup backups directory
        try:
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
        except Exception:
            pass

    # context manager
    def __enter__(self) -> "Transaction":
        return self

    def __exit__(self, exc_type, exc, tb) -> Optional[bool]:
        if exc:
            try:
                self.rollback()
            except Exception:
                pass
            return False  # re-raise the exception
        else:
            try:
                self.commit()
            except Exception:
                pass
            return True
