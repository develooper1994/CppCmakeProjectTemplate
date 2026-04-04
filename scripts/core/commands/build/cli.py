"""CLI parser and entry point for the build command."""
from __future__ import annotations

import argparse

from .commands import (
    cmd_build,
    cmd_check,
    cmd_clean,
    cmd_deploy,
    cmd_extension,
    cmd_docker,
    cmd_watch,
    cmd_diagnose,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool build",
        description="Build system automation",
    )
    sub = parser.add_subparsers(dest="subcommand")

    # build
    p = sub.add_parser("build", help="Configure + compile")
    p.add_argument("--preset", default=None)
    p.add_argument("--profile",
                   choices=["normal", "strict", "hardened", "extreme"],
                   default="normal",
                   help="Apply specific build profile (e.g. hardened)")
    p.add_argument("--sanitizers", nargs="+",
                   choices=["asan", "ubsan", "tsan", "all"],
                   help="Enable granular sanitizers (multiple allowed, or 'all')")
    p.add_argument("--lto", action="store_true", help="Enable Link-Time Optimization")
    p.add_argument("--pgo", choices=["generate", "use"], default=None,
                   help="Profile-Guided Optimization mode")
    p.add_argument("--pgo-dir", default=None, metavar="DIR",
                   help="PGO profile data directory (default: build/pgo-profiles)")
    p.add_argument("--bolt", action="store_true",
                   help="Enable LLVM BOLT post-link optimization targets (requires llvm-bolt)")
    p.add_argument("--openmp", action="store_true", help="Enable OpenMP threading (-DENABLE_OPENMP=ON)")
    p.add_argument("--openmp-simd", action="store_true", dest="openmp_simd",
                   help="Enable OpenMP SIMD only — no libgomp runtime dep (-DENABLE_OPENMP_SIMD=ON)")
    p.add_argument("--auto-parallel", action="store_true", dest="auto_parallel",
                   help="Enable compiler auto-parallelization (-DENABLE_AUTO_PARALLEL=ON)")
    p.add_argument("--qt", action="store_true", help="Enable Qt support (-DENABLE_QT=ON)")
    p.add_argument("--qml", action="store_true", help="Enable Qt QML/Quick (-DENABLE_QT=ON -DENABLE_QML=ON)")
    p.add_argument("--reproducible", action="store_true",
                   help="Enable binary reproducibility (-DENABLE_REPRODUCIBLE=ON)")
    p.add_argument("--allocator", choices=["default", "mimalloc", "jemalloc", "tcmalloc"],
                   default="default",
                   help="Optional allocator backend (default keeps system allocator)")
    p.set_defaults(func=cmd_build)

    # check
    p = sub.add_parser("check", help="Build + test + extension sync")
    p.add_argument("--preset", default=None)
    p.add_argument("--profile",
                   choices=["normal", "strict", "hardened", "extreme"],
                   default="normal",
                   help="Apply specific build profile (e.g. hardened)")
    p.add_argument("--sanitizers", nargs="+",
                   choices=["asan", "ubsan", "tsan", "all"],
                   help="Enable granular sanitizers (multiple allowed, or 'all')")
    p.add_argument("--lto", action="store_true", help="Enable Link-Time Optimization")
    p.add_argument("--pgo", choices=["generate", "use"], default=None,
                   help="Profile-Guided Optimization mode")
    p.add_argument("--pgo-dir", default=None, metavar="DIR",
                   help="PGO profile data directory")
    p.add_argument("--bolt", action="store_true",
                   help="Enable LLVM BOLT post-link optimization targets (requires llvm-bolt)")
    p.add_argument("--openmp", action="store_true", help="Enable OpenMP threading")
    p.add_argument("--openmp-simd", action="store_true", dest="openmp_simd",
                   help="Enable OpenMP SIMD only")
    p.add_argument("--auto-parallel", action="store_true", dest="auto_parallel",
                   help="Enable compiler auto-parallelization")
    p.add_argument("--qt", action="store_true", help="Enable Qt support")
    p.add_argument("--qml", action="store_true", help="Enable Qt QML/Quick")
    p.add_argument("--reproducible", action="store_true",
                   help="Enable binary reproducibility (-DENABLE_REPRODUCIBLE=ON)")
    p.add_argument("--allocator", choices=["default", "mimalloc", "jemalloc", "tcmalloc"],
                   default="default",
                   help="Optional allocator backend (default keeps system allocator)")
    p.add_argument("--no-sync", action="store_true")
    p.set_defaults(func=cmd_check)

    # clean
    p = sub.add_parser("clean", help="Remove build artifacts")
    p.add_argument("targets", nargs="*")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_clean)

    # deploy
    p = sub.add_parser("deploy", help="Remote deploy via rsync")
    p.add_argument("--host", required=True)
    p.add_argument("--path", default="/tmp/cpp_project")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_deploy)

    # extension
    p = sub.add_parser("extension", help="Build .vsix extension")
    p.add_argument("--install", action="store_true")
    p.add_argument("--publish", action="store_true")
    p.set_defaults(func=cmd_extension)

    # docker
    p = sub.add_parser("docker", help="Build inside a Docker container")
    p.add_argument("--preset", default=None, help="CMake preset to pass (default: auto-detected)")
    p.add_argument("--image", default="ubuntu:24.04",
                   help="Docker image to use (default: ubuntu:24.04)")
    p.add_argument("--extra-args", nargs=argparse.REMAINDER, default=[],
                   metavar="ARG", dest="extra_args",
                   help="Extra arguments forwarded to 'tool build build' inside container")
    p.set_defaults(func=cmd_docker)

    # watch
    p = sub.add_parser("watch", help="Auto-rebuild on source changes")
    p.add_argument("--preset", default=None, help="CMake preset to use")
    p.add_argument("--interval", type=float, default=2.0,
                   help="Poll interval in seconds (default: 2.0)")
    p.set_defaults(func=cmd_watch)

    # diagnose
    p = sub.add_parser("diagnose", help="Analyse build log and suggest fixes")
    p.add_argument("logfile", nargs="?", default=None,
                   help="Path to build log file (default: read from stdin)")
    p.set_defaults(func=cmd_diagnose)

    return parser


def main(argv: list[str]) -> None:
    parser = build_parser()
    # Support shorthand forms:
    #  - `tool build extreme`           -> treat as `tool build build --profile extreme`
    #  - `tool build build extreme`     -> treat as `tool build build --profile extreme`
    #  - `tool build check extreme`     -> treat as `tool build check --profile extreme`
    subcommands = {"build", "check", "clean", "deploy", "extension", "docker", "watch", "diagnose"}
    profile_choices = {"normal", "strict", "hardened", "extreme"}

    if argv:
        # Case A: user supplied a bare profile as first token
        if argv[0] in profile_choices:
            argv = ["build", "--profile", argv[0]] + argv[1:]
        # Case B: user supplied a known subcommand followed by a bare profile
        elif argv[0] in subcommands and len(argv) > 1 and argv[1] in profile_choices and not argv[1].startswith("-"):
            argv = [argv[0], "--profile", argv[1]] + argv[2:]

    # Default subcommand: "build"
    args = parser.parse_args(argv if argv else ["build"])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
