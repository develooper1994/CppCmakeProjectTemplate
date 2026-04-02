# Quick Start

## New Project (fastest path)

```bash
python3 scripts/tool.py new MyProject
```

The wizard guides you through name, license, C++ standard, profile, and features.
For automation: `python3 scripts/tool.py new MyProject --non-interactive`

## Existing Clone

```bash
# 1. Install mandatory dependencies (Ubuntu/Debian)
python3 scripts/tool.py setup --install

# 2. Configure + build + test (auto-detects platform preset)
python3 scripts/tool.py build check

# 3. Run the example app
./build/gcc-debug-static-x86_64/apps/main_app/main_app
```
