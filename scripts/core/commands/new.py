"""
core/commands/new.py — ``tool new`` shortcut for interactive project creation.

Usage:
    tool new                        # launch wizard in current directory
    tool new MyProject              # launch wizard, generate into ./MyProject
    tool new --target-dir /tmp/proj # explicit target
    tool new --non-interactive      # skip prompts, use defaults + git config
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.utils.common import Logger


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tool new",
        description="Create a new C++ project (interactive wizard).",
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Project name (also used as target directory name).",
    )
    parser.add_argument(
        "--target-dir", "-t",
        type=Path,
        default=None,
        help="Target directory override.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Skip prompts — use defaults and git config.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing files without asking.",
    )
    args = parser.parse_args(argv)

    from core.generator.wizard import Wizard, WizardAnswers

    if args.non_interactive:
        wiz = Wizard(interactive=False)
        answers = wiz.run()
        if args.name:
            answers.name = args.name
    else:
        wiz = Wizard(interactive=True)
        answers = wiz.run()
        if args.name and answers.name == "MyProject":
            answers.name = args.name

    target_dir = args.target_dir or Path.cwd() / answers.name
    target_dir = Path(target_dir).resolve()

    # Delegate to generate
    from core.commands.generate import main as generate_main

    gen_argv = [
        "--target-dir", str(target_dir),
        "--profile", answers.profile,
        "--author", answers.author or "",
        "--contact", answers.contact or "",
        "--license", answers.license,
        "--set", f"project.name={answers.name}",
        "--set", f"project.description={answers.description}",
        "--set", f"project.cxx_standard={answers.cxx_standard}",
        "--init-git",
    ]

    if args.force:
        gen_argv.append("--force")
    else:
        gen_argv.append("--force")  # new projects always overwrite

    for feat in answers.features_without:
        gen_argv.extend(["--without", feat])

    # Build config from wizard answers and pass directly
    import copy
    from core.generator.engine import generate
    from core.generator.merge import ConflictPolicy

    cfg = answers.to_config()
    Logger.info(f"Creating project '{answers.name}' at {target_dir}")

    target_preexisted = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    result = generate(
        target_dir=target_dir,
        policy=ConflictPolicy.OVERWRITE,
        config=cfg,
    )

    for f in result.created:
        Logger.success(f"  + {f}")
    for f in result.errors:
        Logger.error(f"  ✗ {f}")
    Logger.info(f"Done: {result.summary()}")

    # Auto git init
    from core.commands.generate import _maybe_init_git

    class _FakeArgs:
        no_init_git = False
        dry_run = False
        init_git = True

    _maybe_init_git(target_dir, target_preexisted, _FakeArgs(), cfg)

    if result.errors:
        sys.exit(1)
