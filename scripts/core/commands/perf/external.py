"""External tool subcommands: graph, godbolt."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from core.utils.common import CLIResult, Logger, PROJECT_ROOT, run_proc
from ._helpers import LOGS_DIR, _find_active_build_dir


def _cmd_graph(args) -> CLIResult:
    """Generate CMake dependency graph using --graphviz and optionally render with dot."""
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()
    render: bool = getattr(args, "render", False)
    output_format: str = getattr(args, "format", "svg")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    graph_file = LOGS_DIR / "dependency_graph.dot"

    # CMake must be re-run with --graphviz pointing to a file
    cache_file = build_dir / "CMakeCache.txt"
    if not cache_file.exists():
        return CLIResult(success=False, code=1, message=f"No CMakeCache.txt in {build_dir}")

    # Extract source dir from CMakeCache
    source_dir = None
    for line in cache_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("CMAKE_HOME_DIRECTORY:INTERNAL="):
            source_dir = line.split("=", 1)[1].strip()
            break

    if not source_dir:
        source_dir = str(PROJECT_ROOT)

    Logger.info(f"Generating dependency graph → {graph_file}")
    cmd = [
        "cmake",
        f"--graphviz={graph_file}",
        "-B", str(build_dir),
        "-S", source_dir,
    ]
    rc = run_proc(cmd, check=False)
    if rc != 0:
        return CLIResult(success=False, code=rc, message="cmake --graphviz failed")

    if not graph_file.exists():
        return CLIResult(success=False, code=1, message=f"Graph file not generated: {graph_file}")

    Logger.info(f"Graph written: {graph_file}")

    if render:
        dot = shutil.which("dot")
        if not dot:
            Logger.warn("graphviz 'dot' not found. Install: sudo apt install graphviz")
            Logger.info(
                f"  Render manually: dot -T{output_format} {graph_file} "
                f"-o {LOGS_DIR}/graph.{output_format}"
            )
        else:
            out_img = LOGS_DIR / f"dependency_graph.{output_format}"
            rc2 = run_proc(
                [dot, f"-T{output_format}", str(graph_file), "-o", str(out_img)],
                check=False,
            )
            if rc2 == 0:
                Logger.info(f"Graph rendered → {out_img}")
            else:
                Logger.error("dot rendering failed")

    return CLIResult(
        success=True,
        message=f"Graph: {graph_file}",
        data={"dot_file": str(graph_file)},
    )


# ---------------------------------------------------------------------------
# Godbolt Compiler Explorer integration
# ---------------------------------------------------------------------------


def _cmd_godbolt(args: argparse.Namespace) -> CLIResult:
    """Entry point for `tool perf godbolt`."""
    try:
        _impl_godbolt(args)
        return CLIResult(success=True, message="Godbolt compile complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Godbolt failed.")


def _impl_godbolt(args) -> None:
    """Compile a source file via the Godbolt Compiler Explorer REST API.

    Sends the source to https://godbolt.org/api/compiler/<id>/compile and
    prints the resulting assembly to stdout.  When --save is set the output
    is also written to build_logs/godbolt_<basename>.asm.

    Compiler IDs: g131 = GCC 13.1, clang1800 = Clang 18.0.0, etc.
    Full list: curl -s https://godbolt.org/api/compilers | python3 -m json.tool | grep '"id"'
    """
    import urllib.error
    import urllib.request

    src_path = Path(args.source)
    if not src_path.is_absolute():
        src_path = PROJECT_ROOT / src_path
    if not src_path.exists():
        Logger.error(f"Source file not found: {src_path}")
        raise SystemExit(1)

    source_code = src_path.read_text(encoding="utf-8")
    flags: str = getattr(args, "flags", "-O2 -std=c++17") or "-O2 -std=c++17"
    compiler_id: str = getattr(args, "compiler", None) or "g131"
    save: bool = getattr(args, "save", False)
    json_out: bool = getattr(args, "json_out", False)

    url = f"https://godbolt.org/api/compiler/{compiler_id}/compile"
    payload = json.dumps({
        "source": source_code,
        "options": {
            "userArguments": flags,
            "compilerOptions": {},
            "filters": {
                "binary": False,
                "commentOnly": True,
                "demangle": True,
                "directives": True,
                "intel": True,
                "labels": True,
                "trim": True,
            },
        },
        "lang": "c++",
    }).encode("utf-8")

    Logger.info(
        f"[Godbolt] Compiling '{src_path.name}' with compiler '{compiler_id}' flags '{flags}'"
    )
    Logger.info(f"[Godbolt] Endpoint: {url}")

    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        Logger.error(f"[Godbolt] HTTP {e.code}: {e.reason}")
        raise SystemExit(1)
    except urllib.error.URLError as e:
        Logger.error(f"[Godbolt] Network error: {e.reason}. Check internet connectivity.")
        raise SystemExit(1)

    if json_out:
        print(body)
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        Logger.error("[Godbolt] Failed to parse response JSON.")
        print(body)
        raise SystemExit(1)

    # Format the assembly output
    asm_lines = data.get("asm", [])
    stderr_lines = data.get("stderr", [])
    stdout_lines = data.get("stdout", [])
    exit_code = data.get("code", 0)

    if stdout_lines:
        print("──── stdout ────")
        for line in stdout_lines:
            print(line.get("text", ""))
    if stderr_lines:
        print("──── stderr ────")
        for line in stderr_lines:
            print(line.get("text", ""))

    if not asm_lines:
        Logger.warn("[Godbolt] No assembly output returned (compilation may have failed).")
        if exit_code != 0:
            Logger.error(f"[Godbolt] Compiler exited with code {exit_code}")
            raise SystemExit(1)
        return

    asm_text = "\n".join(line.get("text", "") for line in asm_lines)
    print("\n──── assembly ────")
    print(asm_text)

    if save:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        out_file = LOGS_DIR / f"godbolt_{src_path.stem}.asm"
        header = (
            f"; Godbolt Compiler Explorer output\n"
            f"; Source   : {src_path}\n"
            f"; Compiler : {compiler_id}\n"
            f"; Flags    : {flags}\n\n"
        )
        out_file.write_text(header + asm_text, encoding="utf-8")
        Logger.success(f"[Godbolt] Assembly saved to {out_file}")
