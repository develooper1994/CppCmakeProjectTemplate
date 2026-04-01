#!/usr/bin/env python3
"""Corpus triage and minimization helper.

Uses afl-cmin / afl-tmin when available; falls back to basic dedupe if not.
"""
import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path


LOG = logging.getLogger("triage")


def has_tool(name):
    return shutil.which(name) is not None


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def dedupe_dir(in_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    seen = set()
    for p in sorted(in_dir.iterdir()):
        if p.is_file():
            s = sha256(p)
            if s in seen:
                continue
            seen.add(s)
            shutil.copy2(p, out_dir / p.name)


def run_afl_cmin(in_dir: Path, out_dir: Path, target_bin: str, timeout_ms: int = 10000):
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["afl-cmin", "-i", str(in_dir), "-o", str(out_dir), "-t", str(timeout_ms), "--", target_bin, "@@"]
    LOG.info("Running: %s", " ".join(cmd))
    subprocess.check_call(cmd)


def run_afl_tmin(in_file: Path, out_file: Path, target_bin: str, timeout_ms: int = 10000):
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["afl-tmin", "-i", str(in_file), "-o", str(out_file), "-t", str(timeout_ms), "--", target_bin, "@@"]
    LOG.info("Running: %s", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--target-bin", type=str, required=False)
    p.add_argument("--minimize", action="store_true")
    p.add_argument("--timeout-ms", type=int, default=10000)
    args = p.parse_args()

    in_dir = args.input_dir
    out_dir = args.output_dir

    if not in_dir.exists():
        LOG.error("Input dir not found: %s", in_dir)
        sys.exit(2)

    if args.minimize and args.target_bin and has_tool("afl-cmin"):
        try:
            run_afl_cmin(in_dir, out_dir, args.target_bin, timeout_ms=args.timeout_ms)
            LOG.info("afl-cmin completed; output in %s", out_dir)
            return
        except subprocess.CalledProcessError:
            LOG.exception("afl-cmin failed; falling back to dedupe")

    # fallback: simple dedupe copy
    dedupe_dir(in_dir, out_dir)
    LOG.info("Dedupe copy completed; output in %s", out_dir)


if __name__ == "__main__":
    main()
