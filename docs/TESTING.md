# Testing

## All tests

```bash
# Using ctest preset (recommended)
ctest --preset gcc-debug-static-x86_64 --output-on-failure

# Using unified CLI (configure + build + test)
python3 scripts/tool.py build check --no-sync

# Using toolsolution (auto-configures if needed)
python3 scripts/tool.py sol test

# Via VS Code: click "Tests" in the status bar
```

**With verbose output:**

```bash
ctest --preset gcc-debug-static-x86_64 --output-on-failure --verbose

# Stop on first failure
ctest --preset gcc-debug-static-x86_64 --stop-on-failure
```

## Single library tests

```bash
# Method 1: ctest filter by name
ctest --preset gcc-debug-static-x86_64 -R dummy_lib --output-on-failure

# Method 2: build and run the test binary directly
cmake --build --preset gcc-debug-static-x86_64 --target dummy_lib_tests
./build/gcc-debug-static-x86_64/tests/unit/dummy_lib/dummy_lib_tests

# Run with GTest filter
./build/gcc-debug-static-x86_64/tests/unit/dummy_lib/dummy_lib_tests \
    --gtest_filter="BuildInfoTest.*"

# Method 3: tool lib (builds if needed)
python3 scripts/tool.py lib test dummy_lib

# Method 4: tool sol
python3 scripts/tool.py sol test dummy_lib
```
