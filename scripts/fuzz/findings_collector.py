#!/usr/bin/env python3
"""Collect and optionally minimize AFL findings.

This script scans an AFL output directory (e.g. `afl_out`) for unique
testcases/crashes, copies unique files to a destination folder and, if
possible, runs `afl-cmin` to minimize them.

Use in CI after a short fuzz run to collect artifacts.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def find_candidate_files(afl_out):
    candidates = []
    for sub in ("crashes", "queue", "hangs"):
        d = os.path.join(afl_out, sub)
        if os.path.isdir(d):
            for root, _, files in os.walk(d):
                for f in files:
                    candidates.append(os.path.join(root, f))
    # include top-level
    for root, _, files in os.walk(afl_out):
        for f in files:
            path = os.path.join(root, f)
            if path not in candidates:
                candidates.append(path)
    return candidates


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def copy_unique(inputs, dest_dir):
    ensure_dir(dest_dir)
    seen = {}
    copied = []
    for p in inputs:
        try:
            h = sha256(p)
        except Exception:
            continue
        if h in seen:
            continue
        seen[h] = p
        dst = os.path.join(dest_dir, os.path.basename(p))
        i = 1
        base = dst
        while os.path.exists(dst):
            dst = f"{base}.{i}"
            i += 1
        shutil.copy2(p, dst)
        copied.append(dst)
    return copied


def run_afl_cmin(in_dir, out_dir, target_bin):
    afl_cmin = shutil.which("afl-cmin")
    if not afl_cmin:
        print("afl-cmin not found; skipping cmin step")
        return
    cmd = [afl_cmin, "-i", in_dir, "-o", out_dir, "--", target_bin]
    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print("afl-cmin failed:", e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--afl-out", default="afl_out")
    parser.add_argument("-d", "--dest", default="artifacts/fuzz-findings")
    parser.add_argument("--minimize", action="store_true")
    parser.add_argument("--target-bin", help="path to fuzz binary for minimization")
    args = parser.parse_args()

    afl_out = args.afl_out
    dest = args.dest
    ensure_dir(dest)

    candidates = find_candidate_files(afl_out)
    if not candidates:
        print("No candidate files found in", afl_out)
        return 0

    print(f"Found {len(candidates)} candidate files; copying unique ones...")
    copied = copy_unique(candidates, dest)
    print(f"Copied {len(copied)} unique files to {dest}")

    if args.minimize and args.target_bin:
        try:
            tmp_in = tempfile.mkdtemp(prefix="afl_cmin_in_")
            for p in copied:
                shutil.copy2(p, tmp_in)
            out_min = os.path.join(dest, "minimized_corpus")
            ensure_dir(out_min)
            run_afl_cmin(tmp_in, out_min, args.target_bin)
        except Exception as e:
            print("Minimization step failed:", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
