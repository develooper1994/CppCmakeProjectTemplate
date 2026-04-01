#!/usr/bin/env python3
"""Corpus manager for fuzz targets.

Simple utility to copy local seed files, or download a zip/file into
`tests/fuzz/corpus/<target>/` so CI and local runs can use it.

Usage examples:
  python3 scripts/fuzz/corpus_manager.py list --target secure_ops
  python3 scripts/fuzz/corpus_manager.py copy --source ../myseeds --target secure_ops
  python3 scripts/fuzz/corpus_manager.py download --url https://.../seeds.zip --target secure_ops
"""
import argparse
import os
import shutil
import sys
import urllib.request
import zipfile


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def download_url(url, dest_path):
    tmp = dest_path + ".download"
    print(f"Downloading {url} -> {dest_path}")
    try:
        with urllib.request.urlopen(url) as r, open(tmp, "wb") as out:
            shutil.copyfileobj(r, out)
        os.replace(tmp, dest_path)
        return dest_path
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def extract_zip(zip_path, dest_dir):
    print(f"Extracting {zip_path} -> {dest_dir}")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)


def copy_local(source, dest_dir):
    print(f"Copying from {source} -> {dest_dir}")
    if os.path.isdir(source):
        for root, _, files in os.walk(source):
            for f in files:
                srcf = os.path.join(root, f)
                rel = os.path.relpath(srcf, source)
                dstf = os.path.join(dest_dir, rel)
                ensure_dir(os.path.dirname(dstf))
                shutil.copy2(srcf, dstf)
    elif os.path.isfile(source):
        ensure_dir(dest_dir)
        shutil.copy2(source, os.path.join(dest_dir, os.path.basename(source)))
    else:
        raise FileNotFoundError(source)


def list_corpus(corpus_root, target):
    out = []
    d = os.path.join(corpus_root, target)
    if not os.path.exists(d):
        return out
    for root, _, files in os.walk(d):
        for f in files:
            out.append(os.path.join(root, f))
    return out


def main():
    parser = argparse.ArgumentParser(prog="corpus_manager")
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list")
    p_list.add_argument("--target", default="secure_ops")
    p_list.add_argument("--corpus-root", default="tests/fuzz/corpus")

    p_copy = sub.add_parser("copy")
    p_copy.add_argument("--source", required=True)
    p_copy.add_argument("--target", default="secure_ops")
    p_copy.add_argument("--corpus-root", default="tests/fuzz/corpus")

    p_dl = sub.add_parser("download")
    p_dl.add_argument("--url", required=True)
    p_dl.add_argument("--target", default="secure_ops")
    p_dl.add_argument("--corpus-root", default="tests/fuzz/corpus")

    args = parser.parse_args()

    if args.cmd == "list":
        files = list_corpus(args.corpus_root, args.target)
        if not files:
            print("(no files)")
            return 0
        for f in files:
            print(f)
        return 0

    destdir = os.path.join(args.corpus_root, args.target)
    ensure_dir(destdir)

    if args.cmd == "copy":
        copy_local(args.source, destdir)
        print(f"Copied to {destdir}")
        return 0

    if args.cmd == "download":
        tmpfile = os.path.join(destdir, os.path.basename(args.url))
        downloaded = download_url(args.url, tmpfile)
        # if zip, extract
        try:
            if zipfile.is_zipfile(downloaded):
                extract_zip(downloaded, destdir)
                try:
                    os.remove(downloaded)
                except Exception:
                    pass
            else:
                print(f"Saved {downloaded}")
        except Exception as e:
            print("Error extracting/downloading:", e)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
