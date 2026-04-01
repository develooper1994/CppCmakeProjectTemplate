#!/usr/bin/env python3
"""Simple corpus triage/minimization helper.

Usage examples:
  python3 scripts/fuzz/triage.py --input-dir tests/fuzz/corpus/secure_ops --output-dir artifacts/corpus_min --minimize --target-bin build-afl/fuzz_secure_ops_afl

This script will try to use `afl-cmin` if available (and a target binary is given).
If not available it will fall back to deduplicating inputs by SHA256 and copying
unique seeds to the output directory.
"""
import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def is_tool(name):
    from shutil import which

    return which(name) is not None


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def dedupe_and_copy(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    seen = set()
    copied = 0
    for root, _, files in os.walk(input_dir):
        for fn in files:
            src = os.path.join(root, fn)
            try:
                h = sha256_of_file(src)
            except Exception:
                continue
            if h in seen:
                continue
            seen.add(h)
            dst = os.path.join(output_dir, fn)
            shutil.copy2(src, dst)
            copied += 1
    logging.info("Copied %d unique seeds to %s", copied, output_dir)


def run_afl_cmin(input_dir, output_dir, target_bin):
    # afl-cmin usage: afl-cmin -i in -o out -- <target> [args]
    if not is_tool("afl-cmin"):
        raise RuntimeError("afl-cmin not found in PATH")
    os.makedirs(output_dir, exist_ok=True)
    cmd = ["afl-cmin", "-i", input_dir, "-o", output_dir, "--", target_bin]
    logging.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def parse_args():
    p = argparse.ArgumentParser(description="Corpus triage and minimization helper")
    p.add_argument("--input-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--minimize", action="store_true", help="Try to minimize corpus (afl-cmin if available)")
    p.add_argument("--target-bin", help="Target binary (required for afl-cmin)")
    return p.parse_args()


def main():
    args = parse_args()
    if args.minimize and args.target_bin and is_tool("afl-cmin"):
        try:
            run_afl_cmin(args.input_dir, args.output_dir, args.target_bin)
            return 0
        except subprocess.CalledProcessError as e:
            logging.warning("afl-cmin failed: %s", e)
    # fallback: dedupe & copy
    dedupe_and_copy(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
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
