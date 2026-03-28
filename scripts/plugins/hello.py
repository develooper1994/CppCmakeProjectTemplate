#!/usr/bin/env python3
"""
Example Plugin: Hello
Usage: python3 scripts/tool.py hello --name Mustafa

This file serves as a template for creating dynamic plugins for the 'tool' dispatcher.
To add a new command, simply create a file named 'tool_<command_name>.py' in
the scripts directory and implement a 'main(argv)' function.
"""

# Machine-readable plugin metadata used by `tool plugins describe` and the TUI
PLUGIN_META = {
    "name": "hello",
    "description": "Simple example plugin that greets the provided name.",
    "args": [
        {"name": "name", "help": "Person's name to greet", "type": "string", "required": False}
    ],
}

def main(argv):
    print("👋 Hello from a dynamically discovered plugin!")
    if "--name" in argv:
        idx = argv.index("--name")
        if idx + 1 < len(argv):
            print(f"   Nice to meet you, {argv[idx+1]}!")
        else:
            print("   You didn't provide a name after --name flag.")
    else:
        print("   Try running me with: python3 scripts/tool.py hello --name Mustafa")
