// cmake/ProjectInfo.h
// Convenience single-include header that pulls in all generated build metadata.
//
// Include this instead of including BuildInfo.h, FeatureFlags.h, and
// BuildInfoHelper.h separately.
//
// Requirements (satisfied automatically when the target uses toollib-generated
// CMakeLists.txt + links project_feature_flags):
//   - target_generate_build_info(<target> NAMESPACE <ns>) was called in CMake
//   - target links project_feature_flags (for FeatureFlags.h)
//
// Usage:
//   #include "ProjectInfo.h"
//
//   // Print everything
//   BUILD_INFO_PRINT_ALL(std::cout, my_namespace);
//
//   // Compile-time feature check
//   #if FEATURE_ASAN
//     // running with AddressSanitizer
//   #endif
//
//   // Runtime feature inspection
//   for (const auto& f : project_features::features)
//       std::cout << f.name << ": " << f.enabled << "\n";

#pragma once

// Generated headers (per-target include path set by target_generate_build_info)
#include "BuildInfo.h"

// Project-wide feature flags (include path set by project_feature_flags target)
#include "FeatureFlags.h"

// Convenience helpers: BUILD_INFO_PRINT_ALL, BUILD_INFO_SUMMARY_STRING,
// BUILD_INFO_VERSION_LINE, build_info::print_all(os, ...), build_info::to_string(...)
#include "BuildInfoHelper.h"
