# fuzzable

A small example library used to exercise fuzz harnesses. It intentionally provides a minimal API surface suitable for data-driven fuzzing.

## Contents

- `include/fuzzable/` — public headers
- `src/` — implementation

## Usage

```cmake
target_link_libraries(my_target PRIVATE fuzzable)
```

See [docs/README.md](docs/README.md) for detailed documentation.
