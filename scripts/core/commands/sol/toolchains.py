"""Toolchain and sysroot management subcommands."""
from __future__ import annotations

import json
from pathlib import Path

from core.utils.common import Logger, CLIResult, PROJECT_ROOT, run_proc
from core.utils.command_utils import wrap_command
from ._helpers import (
    TOOLCHAINS_DIR,
    load_presets,
    save_presets,
    _generate_custom_gnu,
)


# ── Toolchain commands ────────────────────────────────────────────────────────

def _impl_cmd_toolchain_list(args) -> None:
    if not TOOLCHAINS_DIR.exists():
        print("No toolchains registered")
        return
    for p in sorted(TOOLCHAINS_DIR.iterdir()):
        if p.is_file():
            print(p.name)


def _impl_cmd_toolchain_add(args) -> None:
    name = getattr(args, "name")
    template = getattr(args, "template")
    prefix = getattr(args, "prefix", "")
    cpu = getattr(args, "cpu", "")
    fpu = getattr(args, "fpu", "")
    gen_preset = getattr(args, "gen_preset", False)
    TOOLCHAINS_DIR.mkdir(parents=True, exist_ok=True)
    dest = TOOLCHAINS_DIR / f"{name}.cmake"
    if dest.exists():
        Logger.warn(f"Toolchain {name} already exists")
        return
    if template == "custom-gnu":
        content = _generate_custom_gnu(name, prefix, cpu, fpu)
    elif template == "arm-none-eabi":
        content = "# arm-none-eabi toolchain stub\n"
    else:
        Logger.error(f"Unknown toolchain template: {template}")
        raise SystemExit(2)
    dest.write_text(content, encoding="utf-8")
    Logger.info(f"Wrote toolchain: {dest}")
    if gen_preset:
        # create a preset that sets CMAKE_TOOLCHAIN_FILE
        pname = f"{name}-preset"
        data = load_presets()
        cfgs = data.setdefault("configurePresets", [])
        if any(p.get("name") == pname for p in cfgs):
            Logger.warn(f"Preset {pname} already exists")
        else:
            cfgs.append({
                "name": pname,
                "generator": "Ninja",
                "binaryDir": f"build/{pname}",
                "toolchainFile": str(dest.as_posix()),
            })
            data.setdefault("buildPresets", []).append({"name": f"{pname}-build", "configurePreset": pname})
            save_presets(data)
            Logger.info(f"Generated preset {pname} referencing toolchain")


def _impl_cmd_toolchain_remove(args) -> None:
    name = getattr(args, "name")
    path = TOOLCHAINS_DIR / f"{name}.cmake"
    if not path.exists():
        Logger.warn(f"Toolchain {name} not found")
        return
    path.unlink()
    Logger.info(f"Removed toolchain {name}")


# ── Sysroot commands ──────────────────────────────────────────────────────────

def _cmd_sysroot_list() -> CLIResult:
    registry_file = PROJECT_ROOT / "sysroots" / "registry.json"
    if not registry_file.exists():
        Logger.info("No sysroots registered yet. Run 'tool sol sysroot add <arch>'.")
        return CLIResult(success=True)
    registry = json.loads(registry_file.read_text(encoding="utf-8"))
    if not registry:
        Logger.info("Registry is empty.")
    else:
        for arch, path in sorted(registry.items()):
            exists = "✓" if Path(path).exists() else "✗ (missing)"
            Logger.info(f"  {arch:15s} → {path}  {exists}")
    return CLIResult(success=True)


def cmd_sysroot_add(args) -> CLIResult:
    try:
        _impl_sysroot_add(args)
        return CLIResult(success=True, message="Sysroot registered.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Sysroot add failed.")


def _impl_sysroot_add(args) -> None:
    """Download/install a cross-compile sysroot and register it for CMake.

    Steps:
    1. Create sysroots/<arch>/ directory in the project root.
    2. If --url is given: download the tarball and extract it there.
       Otherwise, for known arches (aarch64, armv7), suggest/run apt install.
    3. Write sysroots/registry.json  with {arch: path} entries.
    4. Patch cmake/toolchains/<arch>*.cmake to point CMAKE_SYSROOT at the local
       directory (idempotent: only writes if path differs).
    """
    import shutil
    import tarfile
    import urllib.request
    import urllib.error

    arch: str = args.arch
    url: str | None = getattr(args, "url", None)
    dry_run: bool = getattr(args, "dry_run", False)

    sysroots_dir = PROJECT_ROOT / "sysroots"
    sysroot_path = sysroots_dir / arch
    registry_file = sysroots_dir / "registry.json"

    Logger.info(f"[Sysroot] Architecture : {arch}")
    Logger.info(f"[Sysroot] Target path  : {sysroot_path}")

    if dry_run:
        Logger.info("[Sysroot] DRY-RUN — no files will be written.")

    # ── Step 1: create directory ──────────────────────────────────────────────
    if not dry_run:
        sysroot_path.mkdir(parents=True, exist_ok=True)

    # ── Step 2: populate sysroot ──────────────────────────────────────────────
    if url:
        Logger.info(f"[Sysroot] Downloading: {url}")
        tarball = sysroots_dir / f"{arch}_sysroot.tar.gz"
        if not dry_run:
            try:
                with urllib.request.urlopen(url, timeout=120) as resp, \
                        open(tarball, "wb") as fh:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    chunk = 65536
                    while True:
                        block = resp.read(chunk)
                        if not block:
                            break
                        fh.write(block)
                        downloaded += len(block)
                        if total:
                            pct = downloaded * 100 // total
                            print(f"\r  Downloading … {pct}%", end="", flush=True)
                print()
                Logger.success(f"[Sysroot] Downloaded → {tarball}")
            except urllib.error.URLError as e:
                Logger.error(f"[Sysroot] Download failed: {e.reason}")
                raise SystemExit(1)

            Logger.info("[Sysroot] Extracting tarball …")
            try:
                with tarfile.open(tarball) as tf:
                    tf.extractall(path=sysroot_path)  # noqa: S202 — path is local/controlled
                tarball.unlink()
                Logger.success(f"[Sysroot] Extracted → {sysroot_path}")
            except tarfile.TarError as e:
                Logger.error(f"[Sysroot] Extraction failed: {e}")
                raise SystemExit(1)
    else:
        # Try apt for known arches
        _apt_packages: dict[str, list[str]] = {
            "aarch64": ["gcc-aarch64-linux-gnu", "g++-aarch64-linux-gnu",
                        "binutils-aarch64-linux-gnu", "libc6-dev-arm64-cross"],
            "armv7":   ["gcc-arm-linux-gnueabihf", "g++-arm-linux-gnueabihf",
                        "binutils-arm-linux-gnueabihf", "libc6-dev-armhf-cross"],
        }
        if arch in _apt_packages:
            pkgs = _apt_packages[arch]
            Logger.info(f"[Sysroot] Installing cross toolchain via apt: {' '.join(pkgs)}")
            if dry_run:
                Logger.info(f"  [DRY-RUN] would run: sudo apt-get install -y {' '.join(pkgs)}")
            else:
                apt_ok = shutil.which("apt-get")
                if apt_ok:
                    import subprocess
                    result = subprocess.run(["sudo", "apt-get", "install", "-y"] + pkgs,
                                           capture_output=True)
                    if result.returncode != 0:
                        Logger.warn(f"[Sysroot] apt-get failed — sysroot may be incomplete: {result.stderr.decode(errors='replace')}")
                    # Typical apt sysroot location for aarch64 cross
                    apt_sysroot = Path(f"/usr/{arch.replace('aarch64', 'aarch64')}-linux-gnu")
                    if not apt_sysroot.exists():
                        apt_sysroot = Path(f"/usr/{arch}-linux-gnu")
                    if apt_sysroot.exists() and not sysroot_path.exists():
                        sysroot_path.symlink_to(apt_sysroot)
                        Logger.success(f"[Sysroot] Symlinked {sysroot_path} → {apt_sysroot}")
                    elif apt_sysroot.exists():
                        Logger.info(f"[Sysroot] apt sysroot: {apt_sysroot}")
                else:
                    Logger.warn("[Sysroot] apt-get not found. Populate sysroots/{arch} manually.")
        else:
            Logger.warn(
                f"[Sysroot] No --url given and no known package set for arch '{arch}'.\n"
                f"  Populate {sysroot_path} manually and re-run without --url."
            )

    # ── Step 3: update registry ───────────────────────────────────────────────
    registry: dict[str, str] = {}
    if registry_file.exists():
        try:
            registry = json.loads(registry_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    registry[arch] = str(sysroot_path)
    if not dry_run:
        registry_file.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        Logger.success(f"[Sysroot] Registry updated: {registry_file}")
    else:
        Logger.info(f"[Sysroot] Would write registry: {registry_file}")

    # ── Step 4: patch toolchain cmake ─────────────────────────────────────────
    tc_candidates = list(TOOLCHAINS_DIR.glob(f"{arch}*.cmake"))
    if not tc_candidates:
        Logger.info(
            f"[Sysroot] No cmake/toolchains/{arch}*.cmake found.\n"
            f"  Pass -DCMAKE_SYSROOT={sysroot_path} to cmake manually, or create the toolchain file."
        )
    else:
        for tc_file in tc_candidates:
            content = tc_file.read_text(encoding="utf-8")
            new_line = f"set(CMAKE_SYSROOT \"{sysroot_path}\")"
            # If there's already a local sysroot line that matches, skip
            if str(sysroot_path) in content:
                Logger.info(f"[Sysroot] {tc_file.name}: CMAKE_SYSROOT already set to this path.")
                continue
            # Replace existing CMAKE_SYSROOT lines or append
            import re as _re
            if _re.search(r"^\s*set\(CMAKE_SYSROOT", content, _re.MULTILINE):
                new_content = _re.sub(
                    r"^(\s*)set\(CMAKE_SYSROOT[^\)]*\)",
                    lambda m: f"{m.group(1)}{new_line}  # auto-patched by tool sol sysroot add",
                    content,
                    flags=_re.MULTILINE,
                )
            else:
                new_content = content + f"\n# Auto-added by tool sol sysroot add\n{new_line}\n"
            if not dry_run:
                tc_file.write_text(new_content, encoding="utf-8")
                Logger.success(f"[Sysroot] Patched {tc_file.name}: CMAKE_SYSROOT → {sysroot_path}")
            else:
                Logger.info(f"[Sysroot] Would patch {tc_file.name}: CMAKE_SYSROOT → {sysroot_path}")

    Logger.success(
        f"[Sysroot] Done. Use cmake with:\n"
        f"  -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/<your-{arch}-toolchain>.cmake\n"
        f"  -DCMAKE_SYSROOT={sysroot_path}"
    )


# ── Wrapper functions ─────────────────────────────────────────────────────────

def cmd_toolchain_list(args):
    return wrap_command(_impl_cmd_toolchain_list, args)


def cmd_toolchain_add(args):
    return wrap_command(_impl_cmd_toolchain_add, args)


def cmd_toolchain_remove(args):
    return wrap_command(_impl_cmd_toolchain_remove, args)
