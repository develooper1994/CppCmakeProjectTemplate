#!/usr/bin/env python3
"""Download the latest artifact with a given name and extract to output dir.

This is a best-effort helper for CI workflows to reuse previously uploaded
seed-corpus artifacts. It queries the repository artifacts and downloads the
most recent matching artifact name.
"""
import os
import sys
import json
import argparse
import subprocess
import tempfile
import zipfile
from urllib.parse import quote_plus

import urllib.request


def find_artifact(owner, repo, token, artifact_name):
    api = f"https://api.github.com/repos/{owner}/{repo}/actions/artifacts?per_page=100"
    req = urllib.request.Request(api, headers={"Authorization": f"token {token}", "Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    artifacts = data.get("artifacts", [])
    matched = [a for a in artifacts if a.get("name") == artifact_name]
    if not matched:
        return None
    matched.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    return matched[0]


def download_archive(archive_url, token, dest_path):
    # Use curl to handle redirects while preserving Authorization header.
    cmd = [
        "curl",
        "-L",
        "-H",
        f"Authorization: token {token}",
        archive_url,
        "-o",
        dest_path,
    ]
    subprocess.check_call(cmd)


def extract_zip(zip_path, out_dir):
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env)")
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not provided", file=sys.stderr)
        sys.exit(1)
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        print("GITHUB_REPOSITORY not set", file=sys.stderr)
        sys.exit(1)
    owner, repo_name = repo.split("/")
    art = find_artifact(owner, repo_name, token, args.artifact_name)
    if not art:
        print(f"No artifact named {args.artifact_name} found; skipping download", file=sys.stderr)
        sys.exit(0)
    archive_url = art.get("archive_download_url")
    if not archive_url:
        print("artifact has no download url", file=sys.stderr)
        sys.exit(1)
    os.makedirs(args.output, exist_ok=True)
    tmp = tempfile.mktemp(suffix=".zip")
    print("Downloading artifact...", archive_url)
    download_archive(archive_url, token, tmp)
    print("Extracting to", args.output)
    extract_zip(tmp, args.output)
    os.unlink(tmp)
    print("Done")


if __name__ == "__main__":
    main()
