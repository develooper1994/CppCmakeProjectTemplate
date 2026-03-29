# Plugins (Dynamic CLI extensions)

The `scripts/plugins/` directory contains small plugin modules that extend the unified CLI dispatcher (`scripts/tool.py`). Plugins may expose a simple `main(argv)` function and an optional machine-readable `PLUGIN_META` dictionary which powers the TUI and `tool plugins describe` output.

## Discovery & basic commands

- `python3 scripts/tool.py <plugin> [args...]` — run a discovered plugin (e.g. `python3 scripts/tool.py hello --name Mustafa`).
- `python3 scripts/tool.py plugins list` — list discovered plugin names.
- `python3 scripts/tool.py plugins list --json` — machine-readable JSON array of plugin names.
- `python3 scripts/tool.py plugins describe <name>` — print JSON metadata for a plugin (see metadata below).

## Plugin metadata (optional)

- Plugins may expose a top-level `PLUGIN_META` dictionary that the tooling will read without importing the module. If `PLUGIN_META` is absent, the module docstring is used as the description.
- Recommended `PLUGIN_META` shape:

```py
PLUGIN_META = {
    "name": "hello",
    "description": "Example Hello plugin",
    "args": [{"name": "--name", "help": "Your name", "required": False, "default": "world"}]
}
```

The `tool plugins describe <name>` command returns the plugin metadata as JSON. The TUI uses this metadata to populate the Plugins tab (description, args placeholder and quick-run buttons).

## Example plugin (scripts/plugins/hello.py)

```py
#!/usr/bin/env python3
"""
Example Plugin: Hello
Usage: python3 scripts/tool.py hello --name Mustafa
"""

PLUGIN_META = {
    "name": "hello",
    "description": "Example Hello plugin",
    "args": [{"name": "--name", "help": "Your name", "required": False}]
}

def main(argv):
        if "--name" in argv:
                idx = argv.index("--name")
                if idx + 1 < len(argv):
                        print(f"Hello, {argv[idx+1]}!")
                        return
        print("Hello — try: python3 scripts/tool.py hello --name Mustafa")
```

## TUI Integration

- Launch the TUI: `python3 scripts/tui.py`, `python3 -m scripts.tui`, or `python3 scripts/tool.py tui`.
- Plugins tab: the TUI calls `tool plugins list` and `tool plugins describe` to build a discoverable list, shows plugin descriptions, and provides quick-run buttons so you can invoke any plugin with a single keypress.

## Notes

- Plugins should avoid side-effects at import time. Prefer parsing arguments inside `main(argv)`.
- Metadata (`PLUGIN_META`) is optional but improves UI integration.
