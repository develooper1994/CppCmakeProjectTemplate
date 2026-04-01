// cmake/BuildInfoHelper.h
// Convenience wrapper around BuildInfo.h and FeatureFlags.h.
//
// Usage (direct — no template needed):
//   #include "BuildInfo.h"       // defines your_namespace::project_name etc.
//   #include "BuildInfoHelper.h" // defines build_info::print_all(os, ...)
//
//   build_info::print_all(std::cout,
//       your_namespace::project_name, your_namespace::project_version,
//       your_namespace::git_branch,   your_namespace::git_hash,
//       your_namespace::git_describe, your_namespace::git_dirty,
//       your_namespace::build_type,   your_namespace::library_type,
//       your_namespace::architecture, your_namespace::compiler_id,
//       your_namespace::compiler_version, your_namespace::cmake_version,
//       your_namespace::build_timestamp);
//
// Or use the convenience macro (zero boilerplate):
//   BUILD_INFO_PRINT_ALL(std::cout, your_namespace);
//   BUILD_INFO_SUMMARY_STRING(your_namespace)  → std::string
//   BUILD_INFO_VERSION_LINE(your_namespace)    → std::string

#pragma once

#include <ostream>
#include <sstream>
#include <string>
#include <string_view>

#include "FeatureFlags.h"

namespace build_info {

// ── Internal helpers ─────────────────────────────────────────────────────────

inline void _row(std::ostream& os, std::string_view label, std::string_view value, int col = 22) {
    os << "  " << label;
    for (int i = static_cast<int>(label.size()); i < col; ++i)
        os << ' ';
    os << ": " << value << '\n';
}

// ── print_all (explicit args, no template) ───────────────────────────────────

inline void print_all(std::ostream& os,
                      std::string_view project_name,
                      std::string_view project_version,
                      std::string_view git_branch,
                      std::string_view git_hash,
                      std::string_view git_describe,
                      bool git_dirty,
                      std::string_view build_type,
                      std::string_view library_type,
                      std::string_view architecture,
                      std::string_view compiler_id,
                      std::string_view compiler_version,
                      std::string_view cmake_version,
                      std::string_view build_timestamp,
                      bool lto_enabled = false,
                      std::string_view pgo_mode = "off",
                      std::string_view build_cache = "none") {
    os << "\n┌─────────────────────────────────────────────────┐\n";
    os << "│  Build Information\n";
    os << "├─────────────────────────────────────────────────┤\n";
    _row(os, "Project", project_name);
    _row(os, "Version", project_version);
    _row(os, "Build type", build_type);
    _row(os, "Library type", library_type);
    _row(os, "Architecture", architecture);
    _row(os, "Compiler", std::string(compiler_id) + " " + std::string(compiler_version));
    _row(os, "CMake", cmake_version);
    _row(os, "Timestamp", build_timestamp);
    os << "├─────────────────────────────────────────────────┤\n";
    os << "│  Git\n";
    os << "├─────────────────────────────────────────────────┤\n";
    _row(os, "Branch", git_branch);
    _row(os, "Hash", git_hash);
    _row(os, "Describe", git_describe);
    _row(os, "Dirty", git_dirty ? "yes" : "no");
    os << "├─────────────────────────────────────────────────┤\n";
    os << "│  Performance\n";
    os << "├─────────────────────────────────────────────────┤\n";
    _row(os, "LTO", lto_enabled ? "enabled" : "disabled");
    _row(os, "PGO mode", pgo_mode.empty() ? "off" : pgo_mode);
    _row(os, "Build cache", build_cache.empty() ? "none" : build_cache);
    os << "├─────────────────────────────────────────────────┤\n";
    os << "│  Feature Flags\n";
    os << "├─────────────────────────────────────────────────┤\n";
    for (const auto& f : project_features::features)
        _row(os, std::string(f.name), f.enabled ? "[x]" : "[ ]");
    os << "└─────────────────────────────────────────────────┘\n\n";
}

/// Returns a summary as std::string (same content as print_all).
// Suppress cppcheck unusedFunction for this generated helper.
// cppcheck-suppress unusedFunction
inline std::string to_string( // NOLINT
    std::string_view project_name,
    std::string_view project_version,
    std::string_view git_branch,
    std::string_view git_hash,
    std::string_view git_describe,
    bool git_dirty,
    std::string_view build_type,
    std::string_view library_type,
    std::string_view architecture,
    std::string_view compiler_id,
    std::string_view compiler_version,
    std::string_view cmake_version,
    std::string_view build_timestamp,
    bool lto_enabled = false,
    std::string_view pgo_mode = "off",
    std::string_view build_cache = "none") {
    std::ostringstream oss;
    print_all(oss,
              project_name,
              project_version,
              git_branch,
              git_hash,
              git_describe,
              git_dirty,
              build_type,
              library_type,
              architecture,
              compiler_id,
              compiler_version,
              cmake_version,
              build_timestamp,
              lto_enabled,
              pgo_mode,
              build_cache);
    return oss.str();
}

} // namespace build_info

// ── Convenience macros ───────────────────────────────────────────────────────
// These expand the namespace members so you don't have to list them manually.

/// Print all build info for namespace NS to stream S.
#define BUILD_INFO_PRINT_ALL(S, NS)                                                                \
    ::build_info::print_all((S),                                                                   \
                            NS::project_name,                                                      \
                            NS::project_version,                                                   \
                            NS::git_branch,                                                        \
                            NS::git_hash,                                                          \
                            NS::git_describe,                                                      \
                            NS::git_dirty,                                                         \
                            NS::build_type,                                                        \
                            NS::library_type,                                                      \
                            NS::architecture,                                                      \
                            NS::compiler_id,                                                       \
                            NS::compiler_version,                                                  \
                            NS::cmake_version,                                                     \
                            NS::build_timestamp,                                                   \
                            NS::lto_enabled,                                                       \
                            NS::pgo_mode,                                                          \
                            NS::build_cache)

/// Return summary as std::string for namespace NS.
#define BUILD_INFO_SUMMARY_STRING(NS)                                                              \
    ::build_info::to_string(NS::project_name,                                                      \
                            NS::project_version,                                                   \
                            NS::git_branch,                                                        \
                            NS::git_hash,                                                          \
                            NS::git_describe,                                                      \
                            NS::git_dirty,                                                         \
                            NS::build_type,                                                        \
                            NS::library_type,                                                      \
                            NS::architecture,                                                      \
                            NS::compiler_id,                                                       \
                            NS::compiler_version,                                                  \
                            NS::cmake_version,                                                     \
                            NS::build_timestamp,                                                   \
                            NS::lto_enabled,                                                       \
                            NS::pgo_mode,                                                          \
                            NS::build_cache)

/// "Name vX.Y.Z (branch@7chars)" version line.
#define BUILD_INFO_VERSION_LINE(NS)                                                                \
    (std::string(NS::project_name) + " v" + std::string(NS::project_version) + " (" +              \
     std::string(NS::git_branch) + "@" + std::string(NS::git_hash).substr(0, 7) + ")")
