# secure_ops

Safety-focused helpers used by `extreme_app` and fuzz targets. Compiles under the `extreme` hardening profile and demonstrates idiomatic, analyzable, and sanitizer-friendly C++ code.

## Contents

- `include/secure_ops/` — public headers
- `src/` — implementation

## Usage

```cmake
target_link_libraries(my_target PRIVATE secure_ops)
```

See [docs/README.md](docs/README.md) for detailed documentation.
