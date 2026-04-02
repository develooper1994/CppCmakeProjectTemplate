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

static inline uint64_t rotl(uint64_t x, unsigned r) noexcept {{
    return (x << r) | (x >> ((sizeof(x) * 8) - r));
}}

uint64_t process_input(const uint8_t* data, size_t size) noexcept {{
    uint64_t h = 14695981039346656037ULL; // FNV offset basis
    for (size_t i = 0; i < size; ++i) {{
        h ^= static_cast<uint64_t>(data[i]);
        h *= 1099511628211ULL;
        unsigned r = static_cast<unsigned>(data[i] % 13);
        h = rotl(h, r);
    }}
    h ^= static_cast<uint64_t>(size);
    h ^= (h >> 33);
    h *= 0xff51afd7ed558ccdULL;
    h ^= (h >> 33);
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= (h >> 33);
    return h;
}}

}} // namespace {ns}
'''

    if tmpl == "exported":
        return f'''\
#include "{name}/{name}.h"

namespace {ns} {{
// Suppress cppcheck warning about unusedFunction for this public API
// cppcheck-suppress unusedFunction
std::string get_greeting() {{
    return "Hello from {name.replace("_", " ").title()}!";
}}

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

    parts = [f"# {name}", ""]

    if has_build_info:
        version = lib.get("version", "1.0.0")
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

    if tmpl == "exported":
        parts.append(f"auto msg = {ns}::get_greeting();")
    elif tmpl in ("fuzzable", "hasher"):
        parts.append(f"// See {name}_test.cpp for usage examples")
    else:
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

    includes = ["#include <iostream>"]

    if build_info:
        includes.append('#include "ProjectInfo.h"')

    for dep in deps:
        # Find the lib to determine the right API
        lib_match = next((l for l in ctx.libs if l["name"] == dep), None)
        tmpl = _lib_template(lib_match) if lib_match else "default"
        includes.append(f'#include "{dep}/{dep}.h"')

    parts = ["\n".join(includes), ""]

    if gui:
        parts.append(f"""\
int main(int argc, char* argv[]) {{
    (void)argc;
    (void)argv;
""")
    else:
        parts.append("int main() {")

    if build_info:
        parts.append(f"    BUILD_INFO_PRINT_ALL(std::cout, {name}_info);")

    for dep in deps:
        lib_match = next((l for l in ctx.libs if l["name"] == dep), None)
        tmpl = _lib_template(lib_match) if lib_match else "default"
        if tmpl == "exported":
            parts.append(f'    std::cout << {dep}::get_greeting() << "\\n";')
        elif tmpl in ("fuzzable", "hasher"):
            pass  # No simple call for fuzz/hash libs from apps
        else:
            parts.append(f'    std::cout << {dep}::get_name() << "\\n";')

    parts.extend(["    return 0;", "}", ""])
    return "\n".join(parts)


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

    parts = [
        f"// bench_{name}.cpp — Google Benchmark for {name}",
        "",
        "#include <benchmark/benchmark.h>",
    ]

    if tmpl == "exported":
        parts.extend([
            f'#include "{name}/{name}.h"',
            "",
            f"static void BM_{name}_Greeting(benchmark::State& state) {{",
            "    for (auto _ : state) {",
            f"        auto result = {ns}::get_greeting();",
            "        benchmark::DoNotOptimize(result);",
            "        benchmark::ClobberMemory();",
            "    }",
            "}",
            f"BENCHMARK(BM_{name}_Greeting);",
            "",
            "BENCHMARK_MAIN();",
            "",
        ])
    elif tmpl in ("fuzzable", "hasher"):
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


# ---------------------------------------------------------------------------
# Root files
# ---------------------------------------------------------------------------

def _gen_version(ctx: ProjectContext) -> str:
    return ctx.version + "\n"


def _gen_root_readme(ctx: ProjectContext) -> str:
    return f"""\
# {ctx.name}

{ctx.description}

## Build

```bash
python3 scripts/tool.py build
```

## Test

```bash
python3 scripts/tool.py build check
```

## License

{ctx.license}
"""


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
