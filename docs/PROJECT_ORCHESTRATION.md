# Project Orchestration

**In VS Code:** `Ctrl+Shift+P` → *CppTemplate: Project Orchestrator (toolsolution)*

```bash
# List all targets (libs + apps)
python3 scripts/tool.py sol target list

# Build a single target (auto-configures if needed)
python3 scripts/tool.py sol target build main_app
python3 scripts/tool.py sol target build dummy_lib --preset gcc-release-static-x86_64

# Run tests — all or single target
python3 scripts/tool.py sol test
python3 scripts/tool.py sol test dummy_lib

# Manage presets
python3 scripts/tool.py sol preset list
python3 scripts/tool.py sol preset add --compiler gcc --type debug --link static --arch x86_64
python3 scripts/tool.py sol preset remove my-custom-preset

# Manage toolchains
python3 scripts/tool.py sol toolchain list
python3 scripts/tool.py sol toolchain add \
    --name stm32f4 --template arm-none-eabi \
    --cpu cortex-m4 --fpu fpv4-sp-d16 --gen-preset
python3 scripts/tool.py sol toolchain remove stm32f4

# C++ standard — solution-wide or per-library
python3 scripts/tool.py sol upgrade-std --std 20
python3 scripts/tool.py sol upgrade-std --std 20 --target dummy_lib
python3 scripts/tool.py sol upgrade-std --std 20 --dry-run

# View / set base preset cache variables
python3 scripts/tool.py sol config get
python3 scripts/tool.py sol config set ENABLE_ASAN ON

# Full health check
python3 scripts/tool.py sol doctor
```
