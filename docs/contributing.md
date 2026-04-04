# Contributing to CppCmakeProjectTemplate

## Development Setup

```bash
python3 scripts/tool.py setup --install
```

## Code Style

- **C++:** `PascalCase` for classes/structs, `lower_case` for functions/variables
- **Formatting:** `.clang-format` enforced — run `python3 scripts/tool.py format`
- **Static Analysis:** `python3 scripts/tool.py format tidy-fix`

## Testing

```bash
# Run all tests
python3 scripts/tool.py build check --no-sync

# Run specific library tests
cmake --build --preset gcc-debug-static-x86_64 --target <lib>_tests
```

## Pull Request Checklist

- [ ] All tests pass
- [ ] Code formatted with clang-format
- [ ] Documentation updated if needed
- [ ] No new compiler warnings
