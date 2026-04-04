"""
core/generator/sources.py — C++ source file scaffolding.

Generates from [[project.libs]] and [[project.apps]] in tool.toml:
  - libs/<name>/src/<name>.cpp
  - libs/<name>/include/<name>/<name>.h
  - libs/<name>/README.md
  - apps/<name>/src/main.cpp
  - tests/unit/<name>/<name>_test.cpp
  - tests/fuzz/fuzz_<name>.cpp  (if lib.fuzz == true)
  - libs/<name>/benchmarks/bench_<name>.cpp  (if lib.benchmarks == true)
  - VERSION
  - README.md

Template selection is driven by lib fields in tool.toml:
  - export=true        → exported library (get_greeting, export macro)
  - fuzz=true           → fuzzable library (process_input → Result struct)
  - template="hasher"   → hasher library (process_input → uint64_t hash)
  - (default)           → simple library (get_name)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

if __name__ != "__main__":
    from core.generator.engine import ProjectContext


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _lib_template(lib: dict[str, Any]) -> str:
    """Determine which code template to use for a library."""
    tmpl = lib.get("template", "")
    if tmpl == "hasher":
        return "hasher"
    if lib.get("fuzz"):
        return "fuzzable"
    if lib.get("export"):
        return "exported"
    return "default"


# ---------------------------------------------------------------------------
# Library header generation
# ---------------------------------------------------------------------------

def _gen_lib_header(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    lib_type = lib.get("type", "normal")
    is_header_only = lib_type in ("header-only", "interface")
    has_export = lib.get("export", False)
    tmpl = _lib_template(lib)

    if tmpl == "fuzzable":
        return f"""\
// libs/{name}/include/{name}/{name}.h
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace {ns} {{

struct Result {{
    bool ok;
    int value;
    std::string msg;
}};

// Process arbitrary input buffer. Designed to exercise parsing and small
// algorithms without using exceptions (noexcept) so it is compatible with
// hardened/EXTREME profiles that disable exceptions.
Result process_input(const uint8_t* data, size_t size) noexcept;

}} // namespace {ns}
"""

    if tmpl == "hasher":
        return f"""\
// {name}: small, safe processing helpers intended for fuzzing and hardening
#pragma once

#include <cstddef>
#include <cstdint>

namespace {ns} {{

// Process input bytes in a deterministic, safe way and return a 64-bit value.
// Must be noexcept and avoid exceptions/RTTI for extreme hardening builds.
uint64_t process_input(const uint8_t* data, size_t size) noexcept;

}} // namespace {ns}
"""

    # exported or default
    parts = ["#pragma once", ""]

    if tmpl == "exported":
        parts.append("#include <string>")
    else:
        parts.append("#include <string_view>")

    if has_export and not is_header_only:
        parts.append(f'#include "{name}/{name}_export.h"')

    parts.extend(["", f"namespace {ns} {{", ""])

    export_macro = f"{name.upper()}_EXPORT " if (has_export and not is_header_only) else ""

    if tmpl == "exported":
        if has_export and not is_header_only:
            parts.append(f"// Use {name.upper()}_EXPORT for cross-platform visibility")
        parts.append(f"{export_macro}std::string get_greeting();")
    else:
        parts.append(f"{export_macro}std::string_view get_name();")

    parts.extend(["", f"}} // namespace {ns}", ""])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Library source generation
# ---------------------------------------------------------------------------

def _gen_lib_source(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    tmpl = _lib_template(lib)

    if tmpl == "fuzzable":
        return f'''\
// libs/{name}/src/{name}.cpp
// NOLINTBEGIN(cppcoreguidelines-pro-bounds-pointer-arithmetic)
// Raw pointer arithmetic is intentional in this fuzz target library.
#include "{name}/{name}.h"

#include <cctype>
#include <climits>
#include <cstdint>
#include <string>

namespace {ns} {{

static bool parse_int_from_bytes(const uint8_t* buf, size_t len, int& out) noexcept {{
    if (len == 0 || buf == nullptr) {{
        return false;
    }}

    long long accum = 0;
    bool negative = false;
    size_t idx = 0;
    char first_ch = static_cast<char>(buf[0]);
    if (first_ch == '+' || first_ch == '-') {{
        negative = (first_ch == '-');
        idx = 1;
        if (len == 1) {{
            return false;
        }}
    }}

    for (; idx < len; ++idx) {{
        char cur_ch = static_cast<char>(buf[idx]);
        if (std::isdigit(static_cast<unsigned char>(cur_ch)) == 0) {{
            return false;
        }}
        accum = accum * 10 + (cur_ch - '0');
        if (accum > INT32_MAX) {{
            return false;
        }}
    }}

    out = negative ? -static_cast<int>(accum) : static_cast<int>(accum);
    return true;
}}

// cppcheck-suppress unusedFunction
[[maybe_unused]] Result process_input(const uint8_t* data, size_t size) noexcept {{
    Result result{{false, 0, std::string()}};
    if (data == nullptr || size == 0) {{
        result.msg = "empty";
        return result;
    }}

    const uint8_t MESSAGE_TYPE = data[0];

    // Type 1: simple integer parser from payload
    if (MESSAGE_TYPE == 0x01) {{
        if (size < 3) {{
            result.msg = "short1";
            return result;
        }}
        auto payload_len = static_cast<uint16_t>((static_cast<uint32_t>(data[1]) << 8) |
                                                 static_cast<uint32_t>(data[2]));
        if (size < static_cast<size_t>(3 + payload_len)) {{
            result.msg = "len-mismatch";
            return result;
        }}
        const uint8_t* payload_ptr = &data[3];
        int parsed = 0;
        if (parse_int_from_bytes(payload_ptr, payload_len, parsed)) {{
            result.ok = true;
            result.value = parsed;
            result.msg = "ok-int";
            return result;
        }}
        result.msg = "bad-int";
        return result;
    }}

    // Type 2: simple expression a+b where a and b are small integers
    if (MESSAGE_TYPE == 0x02) {{
        const uint8_t* payload_ptr = &data[1];
        const size_t PAYLOAD_LEN = size - 1;
        for (size_t idx = 0; idx < PAYLOAD_LEN; ++idx) {{
            if (static_cast<char>(payload_ptr[idx]) == '+') {{
                int left = 0;
                int right = 0;
                if (parse_int_from_bytes(payload_ptr, idx, left) &&
                    parse_int_from_bytes(payload_ptr + idx + 1, PAYLOAD_LEN - idx - 1, right)) {{
                    result.ok = true;
                    result.value = left + right;
                    result.msg = "expr";
                    return result;
                }}
                break;
            }}
        }}
        result.msg = "noexpr";
        return result;
    }}

    // Type 3: checksum of payload
    if (MESSAGE_TYPE == 0x03) {{
        uint32_t sum = 0U;
        for (size_t idx = 1; idx < size; ++idx) {{
            sum += static_cast<uint32_t>(data[idx]);
        }}
        result.ok = true;
        result.value = static_cast<int>(sum & 0xffffffffU);
        result.msg = "sum";
        return result;
    }}

    result.msg = "unknown-type";
    return result;
}}

}} // namespace {ns}
// NOLINTEND(cppcoreguidelines-pro-bounds-pointer-arithmetic)
'''

    if tmpl == "hasher":
        return f'''\
#include "{name}/{name}.h"

#include <cstddef>
#include <cstdint>

namespace {ns} {{

// NOLINTNEXTLINE(readability-identifier-length)
static inline uint64_t rotl(uint64_t val, unsigned rot) noexcept {{
    return (val << rot) | (val >> ((sizeof(val) * 8) - rot));
}}

uint64_t process_input(const uint8_t* data, size_t size) noexcept {{
    uint64_t hash = 14695981039346656037ULL; // FNV offset basis
    for (size_t i = 0; i < size; ++i) {{
        hash ^= static_cast<uint64_t>(data[i]);
        hash *= 1099511628211ULL;
        auto rot = static_cast<unsigned>(data[i] % 13);
        hash = rotl(hash, rot);
    }}
    hash ^= static_cast<uint64_t>(size);
    hash ^= (hash >> 33);
    hash *= 0xff51afd7ed558ccdULL;
    hash ^= (hash >> 33);
    hash *= 0xc4ceb9fe1a85ec53ULL;
    hash ^= (hash >> 33);
    return hash;
}}

}} // namespace {ns}
'''

    if tmpl == "exported":
        title = name.replace("_", " ").title()
        return f'''\
#include "{name}/{name}.h"

namespace {ns} {{
// Suppress cppcheck warning about unusedFunction for this public API
// cppcheck-suppress unusedFunction
std::string get_greeting() {{ return "Hello from {title}!"; }}

}} // namespace {ns}
'''

    # default
    return f'''\
#include "{name}/{name}.h"

namespace {ns} {{

// cppcheck-suppress unusedFunction
std::string_view get_name() {{
    return "{name}";
}}

}} // namespace {ns}
'''


def _gen_lib_readme(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    lib_type = lib.get("type", "normal")
    tmpl = _lib_template(lib)
    has_build_info = lib.get("build_info", False)
    has_export = lib.get("export", False)
    version = lib.get("version", "1.0.0")
    cxx_standard = lib.get("cxx_standard", "")

    if tmpl == "exported":
        # Rich README for exported libraries: BuildInfo usage, per-lib version, options table
        info_ns = f"{name}_info"
        title = name.replace("_", " ").title()
        parts = [f"# {name}", ""]
        parts.append(f"**Version:** {version} (independent of the solution version)")
        parts.append("")
        parts.append(f"Example library demonstrating per-library versioning, export headers, and")
        parts.append(f"compile-time build metadata via `BuildInfo.h`.")
        parts.append("")
        parts.append("## Usage")
        parts.append("")
        parts.append("```cpp")
        parts.append(f"#include <{name}/{name}.h>")
        parts.append(f'#include "BuildInfo.h"      // {info_ns}::project_version == "{version}"')
        parts.append(f'#include "ProjectInfo.h"    // convenience single-include')
        parts.append("")
        parts.append(f"auto msg = {ns}::get_greeting();")
        parts.append("")
        parts.append("// Access this library's own build metadata")
        parts.append(f"std::cout << {info_ns}::project_name    << \"\\n\";")
        parts.append(f'std::cout << {info_ns}::project_version << "\\n";  // "{version}"')
        parts.append(f"std::cout << {info_ns}::compiler_id     << \"\\n\";")
        parts.append("")
        parts.append("// Print everything at once")
        parts.append(f"BUILD_INFO_PRINT_ALL(std::cout, {info_ns});")
        parts.append("```")
        parts.append("")
        parts.append("## Per-library version")
        parts.append("")
        parts.append("Each library declares its own version in its `CMakeLists.txt`:")
        parts.append("")
        parts.append("```cmake")
        parts.append(f"target_generate_build_info({name}")
        parts.append(f"    NAMESPACE {info_ns}")
        parts.append(f'    PROJECT_VERSION "{version}"   # ← independent from the solution version')
        parts.append(")")
        parts.append("```")
        parts.append("")
        parts.append(f"This version is embedded at compile time into `{info_ns}::project_version`")
        parts.append(f"and is distinct from the top-level solution version (`main_app_info::project_version`).")
        parts.append("")
        parts.append("## Build options")
        parts.append("")
        parts.append("| CMake variable | Default | Effect |")
        parts.append("|---|---|---|")
        uname = name.upper()
        parts.append(f'| `{uname}_CXX_STANDARD` | `""` | Per-lib C++ standard override (14/17/20/23) |')
        parts.append("")
        return "\n".join(parts)

    if tmpl in ("fuzzable", "hasher"):
        # Descriptive README for fuzz/hasher libraries
        if tmpl == "fuzzable":
            desc = "A small example library used to exercise fuzz harnesses. It intentionally provides a minimal API surface suitable for data-driven fuzzing."
        else:
            desc = f"Safety-focused helpers used by `extreme_app` and fuzz targets. Compiles under the `extreme` hardening profile and demonstrates idiomatic, analyzable, and sanitizer-friendly C++ code."

        parts = [f"# {name}", ""]
        parts.append(desc)
        parts.append("")
        parts.append("## Contents")
        parts.append("")
        parts.append(f"- `include/{name}/` — public headers")
        parts.append("- `src/` — implementation")
        parts.append("")
        parts.append("## Usage")
        parts.append("")
        parts.append("```cmake")
        parts.append(f"target_link_libraries(my_target PRIVATE {name})")
        parts.append("```")
        parts.append("")
        parts.append(f"See [docs/README.md](docs/README.md) for detailed documentation.")
        parts.append("")
        return "\n".join(parts)

    # default — generic minimal README
    parts = [f"# {name}", ""]

    if has_build_info:
        parts.append(f"**Version:** {version} (independent of the solution version)")
        parts.append("")

    parts.append(f"{lib_type.capitalize()} library — part of {ctx.name}.")
    parts.append("")
    parts.append("## Usage")
    parts.append("")
    parts.append("```cpp")
    parts.append(f'#include "{name}/{name}.h"')

    if has_build_info:
        parts.append(f'#include "ProjectInfo.h"')

    parts.append("")
    parts.append(f"auto value = {ns}::get_name();")
    parts.append("```")
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Application scaffolding
# ---------------------------------------------------------------------------

def _gen_app_main(app: dict[str, Any], ctx: ProjectContext) -> str:
    name = app["name"]
    deps = app.get("deps", [])
    build_info = app.get("build_info", False)
    gui = app.get("gui", False)
    qml = app.get("qml", False)
    hardening = app.get("hardening", False)

    # Determine special app patterns
    has_hasher_dep = False
    has_exported_dep = False
    for dep in deps:
        lib_match = next((l for l in ctx.libs if l["name"] == dep), None)
        if lib_match:
            tmpl = _lib_template(lib_match)
            if tmpl == "hasher":
                has_hasher_dep = True
            elif tmpl == "exported":
                has_exported_dep = True

    # --- gui app (Qt Widgets + optional QML) ---
    if gui:
        return _gen_app_main_gui(name, deps, qml)

    # --- extreme/hardening app (file fingerprint using hasher lib) ---
    if hardening and has_hasher_dep:
        return _gen_app_main_extreme(name, deps)

    # --- demo app (perf metrics with ScopedTimer) ---
    if not build_info and has_exported_dep and name != "main_app":
        return _gen_app_main_demo(name, deps)

    # --- main_app / default (build_info + greeting) ---
    includes = ["#include <iostream>"]

    if build_info:
        includes.append("")
        includes.append('#include "ProjectInfo.h" // BuildInfo.h + FeatureFlags.h + BuildInfoHelper.h')

    for dep in deps:
        includes.append(f'#include "{dep}/{dep}.h"')

    parts = ["\n".join(includes), ""]
    parts.append("int main() {")

    if build_info:
        parts.append("    // Print all build-time info using the convenience macro")
        parts.append(f"    BUILD_INFO_PRINT_ALL(std::cout, {name}_info);")
        parts.append("")

    for dep in deps:
        lib_match = next((l for l in ctx.libs if l["name"] == dep), None)
        tmpl = _lib_template(lib_match) if lib_match else "default"
        if tmpl == "exported":
            parts.append(f'    std::cout << {dep}::get_greeting() << "\\n";')
        elif tmpl not in ("fuzzable", "hasher"):
            parts.append(f'    std::cout << {dep}::get_name() << "\\n";')

    parts.extend(["    return 0;", "}", ""])
    return "\n".join(parts)


def _gen_app_main_demo(name: str, deps: list[str]) -> str:
    """Generate demo_app with perf::ScopedTimer and ThroughputCounter."""
    dep = deps[0] if deps else "dummy_lib"
    return f'''\
#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>

#include "{dep}/{dep}.h"

// ---------------------------------------------------------------------------
// Lightweight runtime performance metrics helper.
// Uses std::chrono high_resolution_clock for wall-time measurement and a
// simple call counter so callers can compute throughput without pulling in
// extra dependencies.
// ---------------------------------------------------------------------------

namespace perf {{

/// RAII wall-clock timer.  Prints elapsed time on destruction.
class ScopedTimer {{
public:
    explicit ScopedTimer(const char* label)
        : label_(label), start_(std::chrono::high_resolution_clock::now()) {{}}

    ~ScopedTimer() {{
        auto end = std::chrono::high_resolution_clock::now();
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(end - start_).count();
        std::cout << "[perf] " << label_ << ": " << us << " µs\\n";
    }}

    /// Elapsed microseconds so far (non-destructive).
    [[nodiscard]] std::int64_t elapsed_us() const noexcept {{
        auto now = std::chrono::high_resolution_clock::now();
        return std::chrono::duration_cast<std::chrono::microseconds>(now - start_).count();
    }}

private:
    const char* label_;
    std::chrono::high_resolution_clock::time_point start_;
}};

/// Simple throughput counter: records N iterations and prints ops/s.
class ThroughputCounter {{
public:
    explicit ThroughputCounter(const char* label, std::int64_t iterations)
        : label_(label), iters_(iterations), start_(std::chrono::high_resolution_clock::now()) {{}}

    ~ThroughputCounter() {{
        auto end = std::chrono::high_resolution_clock::now();
        double secs = std::chrono::duration<double>(end - start_).count();
        double ops_per_s = (secs > 0.0) ? static_cast<double>(iters_) / secs : 0.0;
        std::cout << "[perf] " << label_ << ": " << iters_ << " ops in "
                  << static_cast<std::int64_t>(secs * 1000) << " ms"
                  << "  →  " << static_cast<std::int64_t>(ops_per_s) << " ops/s\\n";
    }}

private:
    const char* label_;
    std::int64_t iters_;
    std::chrono::high_resolution_clock::time_point start_;
}};

}} // namespace perf

// ---------------------------------------------------------------------------

int main() {{
    std::cout << "=== {name} ===\\n";

    // 1. Basic library call — instrumented with ScopedTimer
    {{
        perf::ScopedTimer t("get_greeting()");
        std::string greeting = {dep}::get_greeting();
        std::cout << "Library says: " << greeting << "\\n";
    }}

    // 2. Throughput demo — 100 000 greeting calls
    {{
        constexpr std::int64_t N = 100'000;
        perf::ThroughputCounter tc("greet loop", N);
        std::string last;
        for (std::int64_t i = 0; i < N; ++i) {{
            last = {dep}::get_greeting();
        }}
        (void)last; // prevent over-aggressive optimisation
    }}

    std::cout << "=== done ===\\n";
    return 0;
}}
'''


def _gen_app_main_extreme(name: str, deps: list[str]) -> str:
    """Generate extreme_app with file fingerprinting (hardening + hasher)."""
    dep = deps[0] if deps else "secure_ops"
    return f'''\
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

#include "{dep}/{dep}.h"

// A small deterministic, memory-safe example that computes a 64-bit
// fingerprint of a file or stdin and prints it. Avoids exceptions/RTTI
// to remain compatible with `-fno-exceptions -fno-rtti` (extreme profile).
int main(int argc, char** argv) {{
    std::vector<uint8_t> buf;
    if (argc > 1) {{
        std::ifstream f(argv[1], std::ios::binary);
        buf.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    }} else {{
        std::istreambuf_iterator<char> it(std::cin);
        std::istreambuf_iterator<char> end;
        while (it != end) {{
            buf.push_back(static_cast<uint8_t>(*it));
            ++it;
        }}
    }}
    uint64_t r = {dep}::process_input(buf.data(), buf.size());
    std::cout << std::hex << r << std::endl;
    return 0;
}}
'''


def _gen_app_main_gui(name: str, deps: list[str], qml: bool) -> str:
    """Generate gui_app with Qt Widgets + optional QML support."""
    dep = deps[0] if deps else "dummy_lib"
    info_ns = f"{name}_info"
    return f'''\
#include <QApplication>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>
#include <QWidget>

#include "BuildInfo.h"
#include "{dep}/{dep}.h"

#ifdef ENABLE_QML_SUPPORT
#include <QQmlApplicationEngine>
#include <QQmlContext>
#endif

int main(int argc, char* argv[]) {{
    QApplication app(argc, argv);

#ifdef ENABLE_QML_SUPPORT
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("backendGreet",
                                             QString::fromStdString({dep}::get_greeting()));
    const QUrl url(
        QStringLiteral("qrc:/qt/qml/main.qml")); // Note: This expects a .qrc file or direct path
    // For simplicity in template, we'll try to load from local file first
    engine.load(QUrl::fromLocalFile("apps/{name}/src/main.qml"));
    if (engine.rootObjects().isEmpty())
        return -1;
#else
    QWidget window;
    window.setWindowTitle(QString::fromStdString(std::string({info_ns}::project_name)));
    window.setMinimumSize(400, 200);

    QVBoxLayout* layout = new QVBoxLayout(&window);

    QLabel* infoLabel = new QLabel(QString("Version: %1\\nCompiler: %2\\nArch: %3")
                                       .arg({info_ns}::project_version.data())
                                       .arg({info_ns}::compiler_id.data())
                                       .arg({info_ns}::architecture.data()));

    QLabel* greetLabel = new QLabel(QString::fromStdString({dep}::get_greeting()));
    greetLabel->setStyleSheet("font-weight: bold; color: blue;");

    QPushButton* button = new QPushButton("Close Application (Widgets)");
    QObject::connect(button, &QPushButton::clicked, &app, &QApplication::quit);

    layout->addWidget(infoLabel);
    layout->addWidget(greetLabel);
    layout->addWidget(button);

    window.show();
#endif

    return app.exec();
}}
'''


# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------

def _gen_unit_test(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    tmpl = _lib_template(lib)
    has_build_info = lib.get("build_info", False)
    suite = "".join(w.capitalize() for w in name.split("_")) + "Test"

    if tmpl == "fuzzable":
        return f'''\
#include <array>
#include <gtest/gtest.h>

#include "{name}/{name}.h"

TEST({suite}, ProcessSimpleSum) {{
    // type 3 -> checksum
    const std::array<uint8_t, 5> K_DATA{{{{0x03, 1, 2, 3, 4}}}};
    const auto RESULT = {ns}::process_input(K_DATA.data(), K_DATA.size());
    EXPECT_TRUE(RESULT.ok);
    EXPECT_EQ(RESULT.value, 1 + 2 + 3 + 4);
}}

TEST({suite}, ParseInteger) {{
    const std::array<uint8_t, 5> K_PAYLOAD{{
        {{0x01, 0x00, 0x02, '4', '2'}}}}; // type=1 len=2 payload="42"
    const auto RESULT = {ns}::process_input(K_PAYLOAD.data(), K_PAYLOAD.size());
    EXPECT_TRUE(RESULT.ok);
    EXPECT_EQ(RESULT.value, 42);
}}
'''

    if tmpl == "hasher":
        uname = name.replace("_", "")
        suite_name = "".join(w.capitalize() for w in name.split("_"))
        return f'''\
#include "{name}/{name}.h"

#include <array>
#include <cstring>
#include <gtest/gtest.h>
#include <vector>

namespace {{

TEST({suite_name}, NullDataZeroSize) {{
    // Must not crash with null pointer and zero size
    auto result = {ns}::process_input(nullptr, 0);
    // Just verify it returns a deterministic value
    EXPECT_EQ(result, {ns}::process_input(nullptr, 0));
}}

TEST({suite_name}, EmptyInput) {{
    const uint8_t kDummy = 0;  // NOLINT(readability-identifier-naming)
    auto result = {ns}::process_input(&kDummy, 0);
    EXPECT_EQ(result, {ns}::process_input(nullptr, 0));
}}

TEST({suite_name}, Determinism) {{
    // Same input must always produce the same output
    const std::array<uint8_t, 8> kInput = {{0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}};  // NOLINT(readability-identifier-naming)
    auto hash_first = {ns}::process_input(kInput.data(), kInput.size());
    auto hash_second = {ns}::process_input(kInput.data(), kInput.size());
    EXPECT_EQ(hash_first, hash_second);
}}

TEST({suite_name}, DifferentInputsDifferentOutputs) {{
    const std::array<uint8_t, 4> kInputA = {{0x01, 0x02, 0x03, 0x04}};  // NOLINT(readability-identifier-naming)
    const std::array<uint8_t, 4> kInputB = {{0x04, 0x03, 0x02, 0x01}};  // NOLINT(readability-identifier-naming)
    auto hash_a = {ns}::process_input(kInputA.data(), kInputA.size());
    auto hash_b = {ns}::process_input(kInputB.data(), kInputB.size());
    EXPECT_NE(hash_a, hash_b);
}}

TEST({suite_name}, AvalancheEffect) {{
    // Flipping a single bit should produce a significantly different hash
    std::array<uint8_t, 16> input_buf = {{}};
    input_buf.fill(0xAA);

    auto base_hash = {ns}::process_input(input_buf.data(), input_buf.size());

    // Flip one bit
    input_buf[7] ^= 0x01;
    auto flipped_hash = {ns}::process_input(input_buf.data(), input_buf.size());

    EXPECT_NE(base_hash, flipped_hash);

    // Count differing bits (expect good avalanche: ~50% of 64 bits differ)
    uint64_t diff = base_hash ^ flipped_hash;
    int bit_diffs = 0;
    while (diff != 0U) {{
        bit_diffs += static_cast<int>(diff & 1U);
        diff >>= 1U;
    }}
    // At least 10 bits should differ for decent avalanche
    EXPECT_GE(bit_diffs, 10);
}}

TEST({suite_name}, VariousSizes) {{
    // Test with sizes 1, 8, 256 — must not crash or hang
    for (size_t size : {{1U, 8U, 256U, 1024U}}) {{
        std::vector<uint8_t> input_vec(size, 0x42);
        auto result = {ns}::process_input(input_vec.data(), input_vec.size());
        // Just verify non-zero (extremely unlikely for a good hash to be 0)
        EXPECT_NE(result, 0U);
    }}
}}

TEST({suite_name}, SizeAffectsOutput) {{
    // Same content but different sizes should produce different hashes
    std::vector<uint8_t> short_vec(4, 0xFF);
    std::vector<uint8_t> long_vec(8, 0xFF);
    auto hash_short = {ns}::process_input(short_vec.data(), short_vec.size());
    auto hash_long = {ns}::process_input(long_vec.data(), long_vec.size());
    EXPECT_NE(hash_short, hash_long);
}}

}} // namespace
'''

    # exported or default
    parts = []

    if tmpl == "exported":
        parts.append(f'// tests/unit/{name}/{name}_test.cpp')
        parts.append(f'#include "{name}/{name}.h"')
        parts.append("")
        parts.append("#include <gtest/gtest.h>")
        parts.append("#include <string>")
        if has_build_info:
            parts.append("")
            parts.append('#include "ProjectInfo.h" // BuildInfo.h + FeatureFlags.h + BuildInfoHelper.h')
        parts.append("")
        parts.append(f"// ── {name} functional tests ───────────────────────────────────────────────")
        parts.append("")
        parts.append(f"TEST({suite}, GetGreetingIsNotEmpty) {{ EXPECT_FALSE({ns}::get_greeting().empty()); }}")
        parts.append("")
        parts.append(f"TEST({suite}, GetGreetingContainsExpectedText) {{")
        title_word = name.replace("_", " ").title().split()[0]
        parts.append(f'    EXPECT_NE({ns}::get_greeting().find("{title_word}"), std::string::npos);')
        parts.append("}")

        if has_build_info:
            info_ns = f"{name}_info"
            parts.append("")
            parts.append("// ── BuildInfo tests ──────────────────────────────────────────────────────────")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, ProjectNameNotEmpty) {{ EXPECT_FALSE({info_ns}::project_name.empty()); }}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, ProjectVersionNotEmpty) {{")
            parts.append(f"    EXPECT_FALSE({info_ns}::project_version.empty());")
            parts.append("}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, CompilerIdNotEmpty) {{ EXPECT_FALSE({info_ns}::compiler_id.empty()); }}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, ArchitectureKnown) {{")
            parts.append(f'    const auto& arch = {info_ns}::architecture;')
            parts.append(f'    EXPECT_TRUE(arch == "x64" || arch == "x86" || arch == "arm"); // NOLINT')
            parts.append("}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, LibraryTypeKnown) {{")
            parts.append(f'    const auto& library_type = {info_ns}::library_type;')
            parts.append(f'    EXPECT_TRUE(library_type == "Static" || library_type == "Shared" ||')
            parts.append(f'                library_type == "Executable"); // NOLINT')
            parts.append("}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, BuildTypeNotEmpty) {{ EXPECT_FALSE({info_ns}::build_type.empty()); }}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, TimestampNotEmpty) {{ EXPECT_FALSE({info_ns}::build_timestamp.empty()); }}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, GitHashNotEmpty) {{ EXPECT_FALSE({info_ns}::git_hash.empty()); }}")
            parts.append("")
            parts.append(f"TEST(BuildInfoTest, VersionLineContainsVersion) {{")
            parts.append(f"    const std::string VERSION_LINE = BUILD_INFO_VERSION_LINE({info_ns});")
            parts.append(f"    EXPECT_NE(VERSION_LINE.find(std::string({info_ns}::project_version)), std::string::npos);")
            parts.append("}")
            parts.append("")
            parts.append("// ── FeatureFlags tests ───────────────────────────────────────────────────────")
            parts.append("")
            parts.append("TEST(FeatureFlagsTest, ArrayNonEmpty) { EXPECT_FALSE(project_features::features.empty()); }")
            parts.append("")
            parts.append("TEST(FeatureFlagsTest, AllNamesNonEmpty) {")
            parts.append("    for (const auto& feature : project_features::features) {")
            parts.append('        EXPECT_FALSE(feature.name.empty()) << "Feature with empty name found";')
            parts.append("    }")
            parts.append("}")
            parts.append("")
            parts.append("TEST(FeatureFlagsTest, GTestFlagIsTrue) {")
            parts.append("    EXPECT_EQ(FEATURE_GTEST, 1);")
            parts.append("    bool found = false;")
            parts.append("    for (const auto& feature : project_features::features) {")
            parts.append('        if (feature.name == "gtest") {')
            parts.append("            EXPECT_TRUE(feature.enabled);")
            parts.append("            found = true;")
            parts.append("        }")
            parts.append("    }")
            parts.append('    EXPECT_TRUE(found) << "\'gtest\' missing from features array";')
            parts.append("}")
            parts.append("")
            parts.append(f"TEST(FeatureFlagsTest, SharedLibsMacroMatchesLibraryType) {{")
            parts.append(f'    bool shared = ({info_ns}::library_type == "Shared");')
            parts.append(f"    EXPECT_EQ(bool(PROJECT_SHARED_LIBS), shared);")
            parts.append("}")
            parts.append("")
            parts.append("// ── Performance metadata tests ───────────────────────────────────────────────")
            parts.append("")
            parts.append("TEST(PerfMetaTest, LtoEnabledIsBool) {")
            parts.append("    // Just verifying the field exists and is a compile-time bool")
            parts.append(f"    EXPECT_TRUE({info_ns}::lto_enabled == true || {info_ns}::lto_enabled == false);")
            parts.append("}")
            parts.append("")
            parts.append("TEST(PerfMetaTest, PgoModeIsKnownValue) {")
            parts.append(f'    const auto& mode = {info_ns}::pgo_mode;')
            parts.append('    EXPECT_TRUE(mode == "off" || mode == "generate" || mode == "use")')
            parts.append('        << "Unexpected pgo_mode: " << mode;')
            parts.append("}")
            parts.append("")
            parts.append("TEST(PerfMetaTest, BuildCacheIsKnownValue) {")
            parts.append(f'    const auto& cache = {info_ns}::build_cache;')
            parts.append('    EXPECT_TRUE(cache == "none" || cache == "ccache" || cache == "sccache")')
            parts.append('        << "Unexpected build_cache: " << cache;')
            parts.append("}")
            parts.append("")
            parts.append("TEST(PerfMetaTest, SummaryStringContainsPerformanceSection) {")
            parts.append("    // NOLINTBEGIN(readability-identifier-naming)")
            parts.append(f"    const std::string summary_text = BUILD_INFO_SUMMARY_STRING({info_ns});")
            parts.append('    EXPECT_NE(summary_text.find("Performance"), std::string::npos)')
            parts.append('        << "Summary missing Performance section";')
            parts.append('    EXPECT_NE(summary_text.find("LTO"), std::string::npos) << "Summary missing LTO row";')
            parts.append('    EXPECT_NE(summary_text.find("PGO"), std::string::npos) << "Summary missing PGO row";')
            parts.append("    // NOLINTEND(readability-identifier-naming)")
            parts.append("}")
            parts.append("")
            parts.append("TEST(PerfMetaTest, LtoFlagConsistentWithFeatureFlags) {")
            parts.append("    // FEATURE_LTO and lto_enabled must agree")
            parts.append("    bool feature_lto = (FEATURE_LTO == 1);")
            parts.append(f"    EXPECT_EQ(feature_lto, {info_ns}::lto_enabled);")
            parts.append("}")

        parts.append("")
        return "\n".join(parts)

    # default template
    return f'''\
#include "{name}/{name}.h"

#include <gtest/gtest.h>
#include <string>

TEST({suite}, GetNameIsNotEmpty) {{
    EXPECT_FALSE({ns}::get_name().empty());
}}

TEST({suite}, GetNameReturnsExpected) {{
    EXPECT_EQ({ns}::get_name(), "{name}");
}}
'''


# ---------------------------------------------------------------------------
# Fuzz harness generation
# ---------------------------------------------------------------------------

def _gen_fuzz_harness(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    tmpl = _lib_template(lib)

    if tmpl == "hasher":
        return f'''\
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

#include "{name}/{name}.h"

#ifdef FUZZ_LIBFUZZER
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {{
    // Keep result volatile to avoid optimization away in fuzz builds
    volatile uint64_t r = {ns}::process_input(data, size);
    (void)r;
    return 0;
}}
#else
int main(int argc, char** argv) {{
    std::vector<uint8_t> buf;
    if (argc > 1) {{
        std::ifstream f(argv[1], std::ios::binary);
        buf.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    }} else {{
        std::istreambuf_iterator<char> it(std::cin);
        std::istreambuf_iterator<char> end;
        while (it != end) {{
            buf.push_back(static_cast<uint8_t>(*it));
            ++it;
        }}
    }}
    volatile uint64_t r = {ns}::process_input(buf.data(), buf.size());
    (void)r;
    return 0;
}}
#endif
'''

    # fuzzable template (default for fuzz=true)
    return f'''\
#include <cstddef>
#include <cstdint>

#include "{name}/{name}.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {{
    // Call into the {name} library to exercise parsing and branches.
    auto result = {ns}::process_input(data, size);
    // Lightweight checks to keep fuzzer informed of interesting results.
    if (result.ok && result.value == 0xdeadbeef) {{
        // Do nothing — just a reachable guard for potential interesting states
        (void)result.msg;
    }}
    return 0;
}}
'''


# ---------------------------------------------------------------------------
# Benchmark scaffolding
# ---------------------------------------------------------------------------

def _gen_benchmark(lib: dict[str, Any], ctx: ProjectContext) -> str:
    name = lib["name"]
    ns = name
    tmpl = _lib_template(lib)

    if tmpl == "exported":
        return _gen_benchmark_exported(name, ns)

    parts = [
        f"// bench_{name}.cpp — Google Benchmark for {name}",
        "",
        "#include <benchmark/benchmark.h>",
    ]

    if tmpl in ("fuzzable", "hasher"):
        parts.extend([
            f'#include "{name}/{name}.h"',
            "#include <array>",
            "#include <vector>",
            "",
            f"static void BM_{name}_SmallInput(benchmark::State& state) {{",
            "    const std::array<uint8_t, 16> data = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,",
            "                                          0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10};",
            "    for (auto _ : state) {",
            f"        auto result = {ns}::process_input(data.data(), data.size());",
            "        benchmark::DoNotOptimize(result);",
            "    }",
            "}",
            f"BENCHMARK(BM_{name}_SmallInput);",
            "",
            f"static void BM_{name}_LargeInput(benchmark::State& state) {{",
            "    std::vector<uint8_t> data(static_cast<size_t>(state.range(0)), 0x42);",
            "    for (auto _ : state) {",
            f"        auto result = {ns}::process_input(data.data(), data.size());",
            "        benchmark::DoNotOptimize(result);",
            "    }",
            "}",
            f"BENCHMARK(BM_{name}_LargeInput)->Range(64, 4096);",
            "",
            "BENCHMARK_MAIN();",
            "",
        ])
    else:
        parts.extend([
            f'#include "{name}/{name}.h"',
            "",
            f"static void BM_{name}_GetName(benchmark::State& state) {{",
            "    for (auto _ : state) {",
            f"        auto result = {ns}::get_name();",
            "        benchmark::DoNotOptimize(result);",
            "    }",
            "}",
            f"BENCHMARK(BM_{name}_GetName);",
            "",
            "BENCHMARK_MAIN();",
            "",
        ])

    return "\n".join(parts)


def _gen_benchmark_exported(name: str, ns: str) -> str:
    """Generate full compute-intensive benchmark for exported libraries."""
    return f'''\
/**
 * bench_{name}.cpp — Google Benchmark: compute-intensive math benchmarks.
 *
 * Demonstrates real performance differences between:
 *   • Sieve of Eratosthenes  (cache-friendly array access)
 *   • Monte Carlo π          (branch-heavy random simulation)
 *   • Matrix multiply        (O(N³) FLOPS, cache-hostile vs tiled)
 *   • Fibonacci (recursive)  (exponential — shows LTO/inlining gain)
 *   • Newton–Raphson √       (FPU-bound convergence loop)
 *   • Sudoku Solver          (backtracking, branch-heavy, deep call stack)
 *   • Mandelbrot Set         (FPU-bound, SIMD/vectorization-friendly)
 *   • 1D Convolution         (memory-bandwidth bound, -funroll-loops effect)
 *   • 2D Convolution         (cache-tiled vs naïve, spatial locality)
 *
 * Build variants to compare (requires -DENABLE_BENCHMARKS=ON):
 *   Debug   : cmake --preset gcc-debug-static-x86_64   -DENABLE_BENCHMARKS=ON
 *   Release : cmake --preset gcc-release-static-x86_64 -DENABLE_BENCHMARKS=ON
 *   LTO     : cmake --preset gcc-release-static-x86_64 -DENABLE_BENCHMARKS=ON -DENABLE_LTO=ON
 *
 * Run:
 *   ./build/<preset>/libs/{name}/bench_{name}
 *   ./build/<preset>/libs/{name}/bench_{name} --benchmark_filter=BM_Sudoku
 *   ./build/<preset>/libs/{name}/bench_{name} --benchmark_format=json \\
 *       --benchmark_out=build_logs/bench_results.json
 *
 * Expected optimization ratios (Debug → Release):
 *   Sudoku     : 5–15×  (inlining, branch prediction improvement)
 *   Mandelbrot : 4–10×  (SIMD / -ffast-math)
 *   Convolution: 3–8×   (-funroll-loops, auto-vectorization)
 *   Sieve      : 2–4×   (auto-vectorization, branch elim)
 */

#include <algorithm>
#include <array>
#include <benchmark/benchmark.h>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <random>
#include <vector>

// ── compiler hints ──────────────────────────────────────────────────────────
#ifdef __GNUC__
#define ATTR_HOT      __attribute__((hot))
#define ATTR_NOINLINE __attribute__((noinline))
#else
#define ATTR_HOT
#define ATTR_NOINLINE
#endif

// ===========================================================================
// 1. Sieve of Eratosthenes
//    Cache-friendly sequential bit operations.
//    Measures: memory bandwidth, branch predictor, auto-vectorization.
// ===========================================================================

ATTR_HOT static std::vector<bool> sieve(std::size_t limit) {{
    std::vector<bool> is_prime(limit + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (std::size_t i = 2; i * i <= limit; ++i) {{
        if (is_prime[i]) {{
            for (std::size_t j = i * i; j <= limit; j += i)
                is_prime[j] = false;
        }}
    }}
    return is_prime;
}}

static void BM_Sieve_10k(benchmark::State& state) {{
    for (auto _ : state) {{
        auto result = sieve(10'000);
        benchmark::DoNotOptimize(result);
    }}
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 10'000);
}}
BENCHMARK(BM_Sieve_10k);

static void BM_Sieve_1M(benchmark::State& state) {{
    for (auto _ : state) {{
        auto result = sieve(1'000'000);
        benchmark::DoNotOptimize(result);
    }}
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 1'000'000);
}}
BENCHMARK(BM_Sieve_1M);

// ===========================================================================
// 2. Monte Carlo π estimation
//    Branch-heavy, FPU-bound. Shows cost of random number generation.
//    Expected ratio inside/total → π/4.
// ===========================================================================

ATTR_HOT static double monte_carlo_pi(std::uint64_t samples) {{
    // Use a fixed seed for reproducibility
    std::mt19937_64 rng(42);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    std::uint64_t inside = 0;
    for (std::uint64_t i = 0; i < samples; ++i) {{
        double x = dist(rng);
        double y = dist(rng);
        if (x * x + y * y <= 1.0)
            ++inside;
    }}
    return 4.0 * static_cast<double>(inside) / static_cast<double>(samples);
}}

static void BM_MonteCarloPi_100k(benchmark::State& state) {{
    for (auto _ : state) {{
        double pi = monte_carlo_pi(100'000);
        benchmark::DoNotOptimize(pi);
    }}
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 100'000);
}}
BENCHMARK(BM_MonteCarloPi_100k);

static void BM_MonteCarloPi_1M(benchmark::State& state) {{
    for (auto _ : state) {{
        double pi = monte_carlo_pi(1'000'000);
        benchmark::DoNotOptimize(pi);
    }}
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 1'000'000);
}}
BENCHMARK(BM_MonteCarloPi_1M);

// ===========================================================================
// 3. Matrix multiply — naïve vs cache-tiled
//    Naïve: O(N³) with poor cache locality (column-major inner loop).
//    Tiled: same complexity, but blocking improves L1/L2 hit rate.
// ===========================================================================

template <std::size_t N>
using Matrix = std::array<std::array<double, N>, N>;

template <std::size_t N>
ATTR_NOINLINE static Matrix<N> matmul_naive(const Matrix<N>& A, const Matrix<N>& B) {{
    Matrix<N> C{{}};
    for (std::size_t i = 0; i < N; ++i)
        for (std::size_t j = 0; j < N; ++j)
            for (std::size_t k = 0; k < N; ++k)
                C[i][j] += A[i][k] * B[k][j];
    return C;
}}

template <std::size_t N, std::size_t TILE = 32>
ATTR_NOINLINE static Matrix<N> matmul_tiled(const Matrix<N>& A, const Matrix<N>& B) {{
    Matrix<N> C{{}};
    for (std::size_t ii = 0; ii < N; ii += TILE)
        for (std::size_t jj = 0; jj < N; jj += TILE)
            for (std::size_t kk = 0; kk < N; kk += TILE)
                for (std::size_t i = ii; i < std::min(ii + TILE, N); ++i)
                    for (std::size_t k = kk; k < std::min(kk + TILE, N); ++k)
                        for (std::size_t j = jj; j < std::min(jj + TILE, N); ++j)
                            C[i][j] += A[i][k] * B[k][j];
    return C;
}}

static void BM_MatMul32_Naive(benchmark::State& state) {{
    constexpr std::size_t N = 32;
    Matrix<N> A{{}}, B{{}};
    // Initialize with non-zero values
    for (std::size_t i = 0; i < N; ++i)
        for (std::size_t j = 0; j < N; ++j) {{
            A[i][j] = static_cast<double>(i + 1);
            B[i][j] = static_cast<double>(j + 1);
        }}
    for (auto _ : state) {{
        auto C = matmul_naive(A, B);
        benchmark::DoNotOptimize(C);
    }}
    // Report GFLOPS
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * N * N * 2 *
                            sizeof(double));
}}
BENCHMARK(BM_MatMul32_Naive);

static void BM_MatMul32_Tiled(benchmark::State& state) {{
    constexpr std::size_t N = 32;
    Matrix<N> A{{}}, B{{}};
    for (std::size_t i = 0; i < N; ++i)
        for (std::size_t j = 0; j < N; ++j) {{
            A[i][j] = static_cast<double>(i + 1);
            B[i][j] = static_cast<double>(j + 1);
        }}
    for (auto _ : state) {{
        auto C = matmul_tiled<N>(A, B);
        benchmark::DoNotOptimize(C);
    }}
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * N * N * 2 *
                            sizeof(double));
}}
BENCHMARK(BM_MatMul32_Tiled);

// ===========================================================================
// 4. Newton–Raphson square root
//    FPU-bound convergence loop; shows benefit of -ffast-math / -O3 vs -O0.
// ===========================================================================

ATTR_HOT static double newton_sqrt(double x) noexcept {{
    if (x <= 0.0)
        return 0.0;
    double guess = x * 0.5;
    // 5 iterations → < 1 ULP error for positive doubles
    for (int i = 0; i < 5; ++i)
        guess = 0.5 * (guess + x / guess);
    return guess;
}}

static void BM_NewtonSqrt(benchmark::State& state) {{
    const int N = static_cast<int>(state.range(0));
    std::vector<double> inputs(static_cast<std::size_t>(N));
    std::iota(inputs.begin(), inputs.end(), 1.0);

    for (auto _ : state) {{
        double sum = 0.0;
        for (int i = 0; i < N; ++i)
            sum += newton_sqrt(inputs[static_cast<std::size_t>(i)]);
        benchmark::DoNotOptimize(sum);
    }}
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * N);
}}
BENCHMARK(BM_NewtonSqrt)->Arg(1'000)->Arg(100'000)->Arg(1'000'000);

// ===========================================================================
// 5. Recursive Fibonacci (exponential baseline)
//    Shows dramatic difference between -O0 and LTO/-O3 with memoization.
//    Intentionally NOT memoized to show worst-case recursion cost.
// ===========================================================================

ATTR_NOINLINE static std::uint64_t fib(unsigned n) noexcept {{
    if (n <= 1)
        return n;
    return fib(n - 1) + fib(n - 2);
}}

static void BM_FibRecursive(benchmark::State& state) {{
    const auto n = static_cast<unsigned>(state.range(0));
    for (auto _ : state) {{
        auto result = fib(n);
        benchmark::DoNotOptimize(result);
    }}
}}
// fib(35) ≈ 9.2M calls — reasonable for a benchmark, < 1 sec at -O2
BENCHMARK(BM_FibRecursive)->Arg(20)->Arg(30)->Arg(35);

// ===========================================================================
// Library-level call (kept for regression baseline)
// ===========================================================================
#include <{name}/{name}.h>

static void BM_Greet_Baseline(benchmark::State& state) {{
    for (auto _ : state) {{
        auto result = {ns}::get_greeting();
        benchmark::DoNotOptimize(result);
        benchmark::ClobberMemory();
    }}
}}
BENCHMARK(BM_Greet_Baseline);

// ===========================================================================
// 6. Sudoku Solver (backtracking)
//    Branch-heavy, deep recursive call stack.
//    Fixed "hard" puzzle — deterministic, no RNG.
//    Measures: branch misprediction cost, inlining depth, call overhead.
//    Expected ratio Debug→Release: 5–15×
// ===========================================================================

using SudokuGrid = std::array<std::array<uint8_t, 9>, 9>;

// A known hard sudoku puzzle (0 = empty cell)
static constexpr SudokuGrid kHardPuzzle = {{{{
    {{8, 0, 0, 0, 0, 0, 0, 0, 0}},
    {{0, 0, 3, 6, 0, 0, 0, 0, 0}},
    {{0, 7, 0, 0, 9, 0, 2, 0, 0}},
    {{0, 5, 0, 0, 0, 7, 0, 0, 0}},
    {{0, 0, 0, 0, 4, 5, 7, 0, 0}},
    {{0, 0, 0, 1, 0, 0, 0, 3, 0}},
    {{0, 0, 1, 0, 0, 0, 0, 6, 8}},
    {{0, 0, 8, 5, 0, 0, 0, 1, 0}},
    {{0, 9, 0, 0, 0, 0, 4, 0, 0}},
}}}};

ATTR_HOT static bool sudoku_valid(const SudokuGrid& g, int row, int col, uint8_t val) noexcept {{
    // Check row and column simultaneously
    for (int i = 0; i < 9; ++i) {{
        if (g[row][i] == val || g[i][col] == val)
            return false;
    }}
    // Check 3×3 box
    const int br = (row / 3) * 3;
    const int bc = (col / 3) * 3;
    for (int r = br; r < br + 3; ++r)
        for (int c = bc; c < bc + 3; ++c)
            if (g[r][c] == val)
                return false;
    return true;
}}

ATTR_NOINLINE static bool solve_sudoku(SudokuGrid& g) noexcept {{
    for (int row = 0; row < 9; ++row) {{
        for (int col = 0; col < 9; ++col) {{
            if (g[row][col] != 0)
                continue;
            for (uint8_t val = 1; val <= 9; ++val) {{
                if (sudoku_valid(g, row, col, val)) {{
                    g[row][col] = val;
                    if (solve_sudoku(g))
                        return true;
                    g[row][col] = 0;
                }}
            }}
            return false; // No valid digit found
        }}
    }}
    return true; // All cells filled
}}

static void BM_SudokuSolver(benchmark::State& state) {{
    for (auto _ : state) {{
        SudokuGrid g = kHardPuzzle;
        bool solved = solve_sudoku(g);
        benchmark::DoNotOptimize(solved);
        benchmark::DoNotOptimize(g);
    }}
}}
BENCHMARK(BM_SudokuSolver);

// ===========================================================================
// 7. Mandelbrot Set
//    FPU-bound inner loop; highly SIMD/vectorization-friendly.
//    -ffast-math allows reassociation → measurable speedup.
//    Measures: floating-point throughput, auto-vectorization width.
//    Expected ratio Debug→Release: 4–10×
// ===========================================================================

ATTR_HOT static int mandelbrot_count(double cx, double cy, int max_iter) noexcept {{
    double x = 0.0, y = 0.0;
    int n = 0;
    while (x * x + y * y <= 4.0 && n < max_iter) {{
        double xtemp = x * x - y * y + cx;
        y = 2.0 * x * y + cy;
        x = xtemp;
        ++n;
    }}
    return n;
}}

template <int W, int H>
ATTR_HOT static long mandelbrot_grid(int max_iter) noexcept {{
    long total = 0;
    for (int py = 0; py < H; ++py) {{
        for (int px = 0; px < W; ++px) {{
            // Map pixel to complex plane: real ∈ [-2.5, 1.0], imag ∈ [-1.25, 1.25]
            double cx = -2.5 + (3.5 * px) / W;
            double cy = -1.25 + (2.5 * py) / H;
            total += mandelbrot_count(cx, cy, max_iter);
        }}
    }}
    return total;
}}

static void BM_Mandelbrot_256(benchmark::State& state) {{
    for (auto _ : state) {{
        long r = mandelbrot_grid<256, 256>(128);
        benchmark::DoNotOptimize(r);
    }}
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 256 * 256);
}}
BENCHMARK(BM_Mandelbrot_256);

static void BM_Mandelbrot_512(benchmark::State& state) {{
    for (auto _ : state) {{
        long r = mandelbrot_grid<512, 512>(256);
        benchmark::DoNotOptimize(r);
    }}
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 512 * 512);
}}
BENCHMARK(BM_Mandelbrot_512);

// ===========================================================================
// 8. 1D Convolution
//    Memory-bandwidth bound; benefits from -funroll-loops and SIMD.
//    Signal: N=65536 doubles. Kernel: K=64 taps.
//    Measures: memory access patterns, loop unrolling, SIMD width.
//    Expected ratio Debug→Release: 3–6×
// ===========================================================================

ATTR_HOT static void convolve_1d(const std::vector<double>& sig,
                                 const std::vector<double>& ker,
                                 std::vector<double>& out) noexcept {{
    const std::size_t N = sig.size();
    const std::size_t K = ker.size();
    const std::size_t half = K / 2;
    for (std::size_t i = 0; i < N; ++i) {{
        double acc = 0.0;
        const std::size_t jstart = (i >= half) ? 0 : half - i;
        const std::size_t jend = std::min(K, N + half - i);
        for (std::size_t j = jstart; j < jend; ++j)
            acc += sig[i + j - half] * ker[j];
        out[i] = acc;
    }}
}}

static void BM_Convolve1D(benchmark::State& state) {{
    constexpr std::size_t N = 65536;
    constexpr std::size_t K = 64;
    std::vector<double> sig(N), ker(K), out(N);
    // Gaussian-like kernel (normalized)
    for (std::size_t i = 0; i < K; ++i) {{
        double x = static_cast<double>(i) - K / 2.0;
        ker[i] = std::exp(-0.5 * x * x / 100.0);
    }}
    std::iota(sig.begin(), sig.end(), 0.0);

    for (auto _ : state) {{
        convolve_1d(sig, ker, out);
        benchmark::DoNotOptimize(out.data());
    }}
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * K * sizeof(double));
}}
BENCHMARK(BM_Convolve1D);

// ===========================================================================
// 9. 2D Convolution — naïve vs cache-tiled
//    Image: 256×256 doubles. Kernel: 7×7.
//    Cache-tiled version processes pixels in blocks to improve L1 hit rate.
//    Contrast with 1D: 2D access patterns stress both row and column strides.
//    Expected ratio (naïve→tiled at -O2): 1.5–3×; Debug→Release: 2–5×
// ===========================================================================

using Image2D = std::vector<std::vector<double>>;

ATTR_NOINLINE static void
convolve_2d_naive(const Image2D& src, const Image2D& ker, Image2D& dst) noexcept {{
    const int H = static_cast<int>(src.size());
    const int W = static_cast<int>(src[0].size());
    const int KH = static_cast<int>(ker.size());
    const int KW = static_cast<int>(ker[0].size());
    const int ph = KH / 2;
    const int pw = KW / 2;
    for (int y = 0; y < H; ++y) {{
        for (int x = 0; x < W; ++x) {{
            double acc = 0.0;
            for (int ky = 0; ky < KH; ++ky) {{
                int sy = y + ky - ph;
                if (sy < 0 || sy >= H)
                    continue;
                for (int kx = 0; kx < KW; ++kx) {{
                    int sx = x + kx - pw;
                    if (sx < 0 || sx >= W)
                        continue;
                    acc += src[sy][sx] * ker[ky][kx];
                }}
            }}
            dst[y][x] = acc;
        }}
    }}
}}

ATTR_NOINLINE static void
convolve_2d_tiled(const Image2D& src, const Image2D& ker, Image2D& dst, int tile = 32) noexcept {{
    const int H = static_cast<int>(src.size());
    const int W = static_cast<int>(src[0].size());
    const int KH = static_cast<int>(ker.size());
    const int KW = static_cast<int>(ker[0].size());
    const int ph = KH / 2;
    const int pw = KW / 2;
    for (int ty = 0; ty < H; ty += tile) {{
        for (int tx = 0; tx < W; tx += tile) {{
            const int yend = std::min(ty + tile, H);
            const int xend = std::min(tx + tile, W);
            for (int y = ty; y < yend; ++y) {{
                for (int x = tx; x < xend; ++x) {{
                    double acc = 0.0;
                    for (int ky = 0; ky < KH; ++ky) {{
                        int sy = y + ky - ph;
                        if (sy < 0 || sy >= H)
                            continue;
                        for (int kx = 0; kx < KW; ++kx) {{
                            int sx = x + kx - pw;
                            if (sx < 0 || sx >= W)
                                continue;
                            acc += src[sy][sx] * ker[ky][kx];
                        }}
                    }}
                    dst[y][x] = acc;
                }}
            }}
        }}
    }}
}}

static Image2D make_image(int H, int W, double fill = 1.0) {{
    return Image2D(H, std::vector<double>(W, fill));
}}

static Image2D make_kernel_2d(int KH, int KW) {{
    Image2D k(KH, std::vector<double>(KW));
    double sigma = 1.5;
    double sum = 0.0;
    for (int y = 0; y < KH; ++y) {{
        for (int x = 0; x < KW; ++x) {{
            double dy = y - KH / 2.0, dx = x - KW / 2.0;
            k[y][x] = std::exp(-(dx * dx + dy * dy) / (2.0 * sigma * sigma));
            sum += k[y][x];
        }}
    }}
    // Normalize
    for (auto& row : k)
        for (auto& v : row)
            v /= sum;
    return k;
}}

static void BM_Convolve2D_Naive(benchmark::State& state) {{
    constexpr int H = 256, W = 256, KH = 7, KW = 7;
    auto src = make_image(H, W);
    auto ker = make_kernel_2d(KH, KW);
    auto dst = make_image(H, W, 0.0);

    for (auto _ : state) {{
        convolve_2d_naive(src, ker, dst);
        benchmark::DoNotOptimize(dst[0][0]);
    }}
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * H * W * KH * KW *
                            sizeof(double));
}}
BENCHMARK(BM_Convolve2D_Naive);

static void BM_Convolve2D_Tiled(benchmark::State& state) {{
    constexpr int H = 256, W = 256, KH = 7, KW = 7;
    auto src = make_image(H, W);
    auto ker = make_kernel_2d(KH, KW);
    auto dst = make_image(H, W, 0.0);

    for (auto _ : state) {{
        convolve_2d_tiled(src, ker, dst);
        benchmark::DoNotOptimize(dst[0][0]);
    }}
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * H * W * KH * KW *
                            sizeof(double));
}}
BENCHMARK(BM_Convolve2D_Tiled);

BENCHMARK_MAIN();
'''


# ---------------------------------------------------------------------------
# Root files
# ---------------------------------------------------------------------------

def _gen_version(ctx: ProjectContext) -> str:
    return ctx.version + "\n"


_STANDARD_DOC_PAGES = [
    ("Quick Start", "QUICK_START"),
    ("Project Structure", "PROJECT_STRUCTURE"),
    ("Embedded & Cross-Compilation Guide", "EMBEDDED"),
    ("Building", "BUILDING"),
    ("Testing", "TESTING"),
    ("Build Settings", "BUILD_SETTINGS"),
    ("Dependencies", "DEPENDENCIES"),
    ("Library Management", "LIBRARY_MANAGEMENT"),
    ("Plugins", "PLUGINS"),
    ("Project Orchestration", "PROJECT_ORCHESTRATION"),
    ("Compile-time Build Info", "BUILD_INFO"),
    ("Starting a New Project", "STARTING_PROJECT"),
    ("CLI Usage Reference", "USAGE"),
    ("Performance", "PERFORMANCE"),
    ("CI / Quality Guards", "CI"),
    ("Capabilities Reference", "CAPABILITIES"),
    ("Roadmap & Ideas", "ROADMAP"),
]


def _gen_root_readme(ctx: ProjectContext) -> str:
    homepage = getattr(ctx, "homepage", "")
    author = getattr(ctx, "author", "")
    cxx_std = getattr(ctx, "cxx_standard", "17")
    cmake_min = getattr(ctx, "cmake_minimum", "3.25")
    has_docs = getattr(ctx, "docs", {}).get("generate", True)

    parts = [f"# {ctx.description}", ""]

    # Badges
    if homepage:
        badge_parts = []
        badge_parts.append(
            f"[![CI]({homepage}/actions/workflows/ci.yml/badge.svg)]"
            f"({homepage}/actions/workflows/ci.yml)"
        )
        badge_parts.append(
            f"[![License: {ctx.license}](https://img.shields.io/badge/License-{ctx.license}-blue.svg)](LICENSE)"
        )
        badge_parts.append(
            f"[![CMake: {cmake_min}+](https://img.shields.io/badge/CMake-{cmake_min}+-informational.svg)](https://cmake.org)"
        )
        badge_parts.append(
            f"[![C++{cxx_std}](https://img.shields.io/badge/C++-{cxx_std}-blue.svg)](https://isocpp.org/)"
        )
        badge_parts.append(
            f"[![Platform](https://img.shields.io/badge/Platform-Linux%20|%20Windows%20|%20macOS-lightgrey)]({homepage})"
        )
        parts.append(" ".join(badge_parts))
        parts.append("")

    parts.append(
        "A professional, multi-target C++ project skeleton with cross-platform presets, "
        "per-library versioning, compile-time feature detection, and full tooling automation."
    )
    parts.append("")

    # Documentation Index
    if has_docs:
        parts.append("## Documentation Index")
        parts.append("")
        parts.append(
            "The full project README has been split into focused topic pages inside "
            "the `docs/` directory. Use the links below to jump to what you need."
        )
        parts.append("")
        for label, page in _STANDARD_DOC_PAGES:
            parts.append(f"- **{label}:** [docs/{page}.md](docs/{page}.md)")
        parts.append("")
        parts.append(
            "If you'd like these pages further split "
            "(for example `docs/BUILDING.md` → `docs/VS_CODE.md`, `docs/PRESETS.md`), "
            "tell me which area to subdivide next."
        )
        parts.append("")
        parts.append(
            "This repository's full documentation was long; the complete README has been "
            "moved to the `docs/README_FULL.md` file. The short quick-start is below — "
            "for all details, examples and the full reference, see the full document."
        )
        parts.append("")

    # Quick Start
    parts.append("## Quick Start")
    parts.append("")
    parts.append("```bash")
    parts.append("# Create a new project interactively")
    parts.append("python3 scripts/tool.py new MyProject")
    parts.append("")
    parts.append("# Or non-interactive with defaults")
    parts.append("python3 scripts/tool.py new MyProject --non-interactive")
    parts.append("```")
    parts.append("")
    parts.append("For an existing clone:")
    parts.append("")
    parts.append("```bash")
    parts.append("# 1. Install mandatory dependencies (Ubuntu/Debian)")
    parts.append("python3 scripts/tool.py setup --install")
    parts.append("")
    parts.append("# 2. Configure + build + test (auto-detects platform preset)")
    parts.append("python3 scripts/tool.py build check")
    parts.append("")
    parts.append("# 3. Run the example app")
    # Find a build_info app for the example path
    example_app = "main_app"
    for app in ctx.apps:
        if app.get("build_info", False):
            example_app = app["name"]
            break
    default_preset = ctx.presets.get("default_preset", "gcc-debug-static-x86_64")
    parts.append(f"./build/{default_preset}/apps/{example_app}/{example_app}")
    parts.append("```")
    parts.append("")

    # Footer
    if has_docs:
        parts.append(
            "Full documentation: [docs/README_FULL.md](docs/README_FULL.md) | "
            "Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md) | "
            "Capabilities: [docs/CAPABILITIES.md](docs/CAPABILITIES.md) | "
            "Embedded guide: [docs/EMBEDDED.md](docs/EMBEDDED.md)"
        )
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    is_minimal = str(getattr(ctx, "profile", "full") or "full").strip().lower() == "minimal"

    # Root files
    files["VERSION"] = _gen_version(ctx)
    files["README.md"] = _gen_root_readme(ctx)

    for lib in ctx.libs:
        name = lib["name"]
        lib_type = lib.get("type", "normal")
        is_header_only = lib_type in ("header-only", "interface")

        # Header
        files[f"libs/{name}/include/{name}/{name}.h"] = _gen_lib_header(lib, ctx)

        # Source (not for header-only)
        if not is_header_only:
            files[f"libs/{name}/src/{name}.cpp"] = _gen_lib_source(lib, ctx)

        # README / tests are omitted for the lighter minimal profile
        if not is_minimal:
            files[f"libs/{name}/README.md"] = _gen_lib_readme(lib, ctx)

        if ctx.tests.get("auto_generate", True) and not is_minimal:
            files[f"tests/unit/{name}/{name}_test.cpp"] = _gen_unit_test(lib, ctx)

        if lib.get("fuzz") and ctx.tests.get("fuzz") and not is_minimal:
            files[f"tests/fuzz/fuzz_{name}.cpp"] = _gen_fuzz_harness(lib, ctx)

        # Benchmarks
        if lib.get("benchmarks") and not is_minimal:
            files[f"libs/{name}/benchmarks/bench_{name}.cpp"] = _gen_benchmark(lib, ctx)

    for app in ctx.apps:
        name = app["name"]
        files[f"apps/{name}/src/main.cpp"] = _gen_app_main(app, ctx)

    return files
