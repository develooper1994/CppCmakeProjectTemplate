#!/usr/bin/env python3
"""
core/commands/plugins.py — Plugin discovery and listing for `tool`.

Provides a small `plugins list` command to enumerate available plugins
under `scripts/plugins/`.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
import importlib

# Path bootstrap (scripts/)
_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.utils.common import CLIResult
from core.utils.command_utils import wrap_command
import pkgutil


def discover_plugins() -> list[str]:
    plugin_dir = _SCRIPTS / "plugins"
    if not plugin_dir.exists():
        return []
    names = []
    try:
        for finder, name, ispkg in pkgutil.iter_modules([str(plugin_dir)]):
            names.append(name)
    except Exception:
        # fallback to file scan
        for p in sorted(plugin_dir.iterdir()):
            if p.is_file() and p.suffix == ".py" and not p.name.startswith("_"):
                names.append(p.stem)
    return sorted(names)


def _plugin_file(name: str) -> Path | None:
    plugin_dir = _SCRIPTS / "plugins"
    p1 = plugin_dir / f"{name}.py"
    if p1.exists():
        return p1
    p2 = plugin_dir / name / "__init__.py"
    if p2.exists():
        return p2
    return None


def _parse_plugin_meta(path: Path, name: str) -> dict:
    """Parse plugin metadata from source file without importing.

    Looks for a top-level `PLUGIN_META = {...}` assignment and module
    docstring. Returns a dict with keys: name, description, args.
    """
    try:
        src = path.read_text(encoding="utf-8")
        mod = ast.parse(src)
        doc = ast.get_docstring(mod) or ""
        meta = None
        for node in mod.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "PLUGIN_META":
                        try:
                            meta = ast.literal_eval(node.value)
                        except Exception:
                            meta = None
                        break
                if meta is not None:
                    break
        if not isinstance(meta, dict):
            meta = {"name": name, "description": doc, "args": []}
        else:
            meta = dict(meta)
            meta.setdefault("name", name)
            meta.setdefault("description", doc)
            meta.setdefault("args", [])
        return meta
    except Exception:
        return {"name": name, "description": "", "args": []}


def validate_plugin_meta(meta: dict) -> dict:
    """Validate and normalize plugin metadata structure.

    Ensures `name` and `description` exist and that `args` is a list
    of dictionaries with canonical keys: `name`, `help`, `type`,
    `required`, `default`.
    Supported types: `string` (default), `int`, `bool`, `flag`.
    """
    if not isinstance(meta, dict):
        raise ValueError("plugin meta must be a dict")
    name = str(meta.get("name", ""))
    description = str(meta.get("description", ""))
    raw_args = meta.get("args", []) or []
    validated = []
    for a in raw_args:
        # `arg_name` may be assigned from a str or from a dict lookup; declare
        # as Optional[str] to keep type-checkers happy across branches.
        arg_name: str | None = None
        if isinstance(a, str):
            arg_name = a
            arg_help = ""
            arg_type = "flag"
            required = False
            default = None
        elif isinstance(a, dict):
            arg_name = a.get("name")
            if not arg_name:
                # skip malformed arg entries
                continue
            arg_help = str(a.get("help", ""))
            arg_type = str(a.get("type", "string")).lower()
            if arg_type == "str":
                arg_type = "string"
            if arg_type == "number":
                arg_type = "int"
            if arg_type not in ("string", "int", "bool", "flag"):
                arg_type = "string"
            required = bool(a.get("required", False))
            default = a.get("default", None)
            # normalize default according to type
            if default is not None:
                try:
                    if arg_type == "int":
                        default = int(default)
                    elif arg_type == "bool":
                        default = bool(default)
                    else:
                        default = str(default)
                except Exception:
                    default = None
        else:
            continue
        validated.append({
            "name": str(arg_name),
            "help": arg_help,
            "type": arg_type,
            "required": required,
            "default": default,
        })
    return {"name": name, "description": description, "args": validated}


def _impl_cmd_list(args) -> None:
    names = discover_plugins()
    if getattr(args, "json", False):
        print(json.dumps(names, indent=2, ensure_ascii=False))
        return
    if not names:
        print("(no plugins found)")
        return
    for n in names:
        print(n)


def cmd_list(args):
    return wrap_command(_impl_cmd_list, args)


def _impl_cmd_describe(args) -> None:
    name = getattr(args, "name")
    p = _plugin_file(name)
    if p is None:
        print(f"Plugin not found: {name}")
        raise SystemExit(2)
    meta = _parse_plugin_meta(p, name)
    # Validate/normalize before returning machine-readable metadata
    try:
        meta = validate_plugin_meta(meta)
    except Exception:
        # fallback to best-effort meta when validation fails
        pass
    # Default to JSON output for machine consumption
    print(json.dumps(meta, indent=2, ensure_ascii=False))


def cmd_describe(args):
    return wrap_command(_impl_cmd_describe, args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool plugins", description="List available plugins")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("list", help="List discovered plugins")
    p.add_argument("--json", action="store_true", help="Output JSON array")
    p.set_defaults(func=cmd_list)
    # describe
    p = sub.add_parser("describe", help="Show plugin metadata (JSON)")
    p.add_argument("name", help="Plugin module name")
    p.add_argument("--json", action="store_true", help="Output JSON (default)")
    p.set_defaults(func=cmd_describe)
    return parser


def main(argv: list[str]) -> None:
    # If first arg is not a known subcommand (list/describe) but matches
    # a discovered plugin name, forward the invocation to that plugin's
    # main(argv) so `tool plugins hello --name X` behaves like
    # `tool hello --name X`.
    if argv:
        first = argv[0]
        if first not in ("list", "describe"):
            p = _plugin_file(first)
            if p is not None:
                # import and delegate to plugins.<name>.main
                try:
                    mod = importlib.import_module(f"plugins.{first}")
                    if hasattr(mod, "main"):
                        # pass remaining args to plugin
                        try:
                            mod.main(argv[1:])
                            return
                        except SystemExit:
                            raise
                        except Exception as e:
                            print(f"Plugin error: {e}")
                            raise SystemExit(1)
                    else:
                        print(f"Plugin {first} has no main()")
                        raise SystemExit(2)
                except Exception as e:
                    print(f"Failed to load plugin {first}: {e}")
                    raise SystemExit(2)
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv[1:])
