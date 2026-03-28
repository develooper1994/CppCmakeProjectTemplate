#!/usr/bin/env python3
"""
Publish a .vsix file to GitHub Releases for the current repository.

Usage: python3 scripts/publish_vsix.py [path/to/file.vsix] [tag]

If no file is provided the first .vsix in extension/ is used. If no tag
is provided, 'v1.03' is used by default (this repo already has that tag).

This script will try to extract a token embedded in the remote.origin.url
(`https://<token>@github.com/...`) or fall back to the environment variable
`GITHUB_TOKEN`.
"""
from __future__ import annotations

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def get_vsix(path_arg: str | None) -> Path:
    repo = Path(__file__).resolve().parents[1]
    if path_arg:
        p = Path(path_arg)
        if not p.exists():
            raise SystemExit(f"VSIX not found: {p}")
        return p
    cand = list((repo / "extension").glob("*.vsix"))
    if not cand:
        raise SystemExit("No .vsix found in extension/")
    return cand[0]


def get_token() -> str | None:
    # Try env var first
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t
    # Try to extract from remote URL
    try:
        out = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], stderr=subprocess.DEVNULL)
        url = out.decode().strip()
        m = re.match(r"https://([^@]+)@github.com/([^/]+)/([^/.]+)(?:.git)?", url)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def create_release(owner: str, repo: str, tag: str, token: str, name: str, body: str) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    data = json.dumps({"tag_name": tag, "name": name, "body": body, "draft": False, "prerelease": False}).encode("utf-8")
    req = Request(url, data=data, headers={"Authorization": f"token {token}", "Content-Type": "application/json", "User-Agent": "publish-vsix-script"}, method="POST")
    try:
        with urlopen(req) as r:
            return json.load(r)
    except HTTPError as e:
        try:
            payload = e.read().decode()
            j = json.loads(payload)
            raise SystemExit(f"Create release failed: {j.get('message')} - {j.get('errors', j.get('documentation_url'))}")
        except Exception:
            raise SystemExit(f"Create release failed: HTTP {e.code}")


def upload_asset(upload_url_template: str, filepath: Path, token: str) -> dict:
    # upload_url_template looks like: https://uploads.github.com/repos/:owner/:repo/releases/:id/assets{?name,label}
    upload_url = upload_url_template.split("{")[0]
    name = filepath.name
    url = f"{upload_url}?name={name}"
    with filepath.open('rb') as f:
        data = f.read()
    req = Request(url, data=data, headers={"Authorization": f"token {token}", "Content-Type": "application/octet-stream", "User-Agent": "publish-vsix-script"}, method="POST")
    try:
        with urlopen(req) as r:
            return json.load(r)
    except HTTPError as e:
        try:
            payload = e.read().decode()
            j = json.loads(payload)
            raise SystemExit(f"Upload failed: {j.get('message')} - {j.get('errors', j.get('documentation_url'))}")
        except Exception:
            raise SystemExit(f"Upload failed: HTTP {e.code}")


def parse_owner_repo() -> tuple[str, str]:
    try:
        out = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], stderr=subprocess.DEVNULL).decode().strip()
        m = re.match(r"https://[^@]+@github.com/([^/]+)/([^/.]+)(?:.git)?", out)
        if m:
            return m.group(1), m.group(2)
        m2 = re.match(r"https://github.com/([^/]+)/([^/.]+)(?:.git)?", out)
        if m2:
            return m2.group(1), m2.group(2)
    except Exception:
        pass
    raise SystemExit("Could not determine owner/repo from git remote URL")


def main():
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    tag = sys.argv[2] if len(sys.argv) > 2 else "v1.03"
    vsix = get_vsix(path_arg)
    token = get_token()
    if not token:
        raise SystemExit("No GitHub token found (set GITHUB_TOKEN or embed token in remote.origin.url)")
    owner, repo = parse_owner_repo()
    print(f"Creating release {tag} for {owner}/{repo}...")
    rel = create_release(owner, repo, tag, token, tag, f"Automated release for {tag}")
    upload_url = rel.get('upload_url')
    if not upload_url:
        raise SystemExit("Release created but no upload_url returned")
    print(f"Uploading asset {vsix.name}...")
    asset = upload_asset(upload_url, vsix, token)
    print(f"Uploaded: {asset.get('browser_download_url')}")


if __name__ == '__main__':
    main()
