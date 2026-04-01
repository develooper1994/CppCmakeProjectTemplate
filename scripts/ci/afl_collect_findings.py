#!/usr/bin/env python3
"""Collect AFL output directory into a findings zip file."""
import os
import sys
import argparse
import zipfile


def zip_dir(src, dest):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src):
            for f in files:
                path = os.path.join(root, f)
                arcname = os.path.relpath(path, src)
                zf.write(path, arcname)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="findings.zip")
    args = parser.parse_args()
    if not os.path.exists(args.input):
        print("Input path not found:", args.input, file=sys.stderr)
        sys.exit(0)
    zip_dir(args.input, args.output)
    print("Wrote", args.output)


if __name__ == "__main__":
    main()
