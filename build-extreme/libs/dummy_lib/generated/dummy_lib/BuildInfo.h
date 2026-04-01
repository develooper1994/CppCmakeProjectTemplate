#pragma once

#include <string_view>

namespace dummy_lib_info {

constexpr std::string_view project_name = "CppCmakeProjectTemplate";
constexpr std::string_view project_version = "2.5.0";
constexpr std::string_view git_hash = "be8b01a77596a6176cc0dd3514fe64e8e222b24f";
constexpr std::string_view git_branch = "tidy/clang-tidy-fixes";
constexpr std::string_view git_describe = "v1.0.6-11-gbe8b01a-dirty";
constexpr bool git_dirty = true;
constexpr std::string_view build_type = "Debug";
constexpr std::string_view compiler_id = "GNU";
constexpr std::string_view compiler_version = "13.3.0";
constexpr std::string_view architecture = "x64";
constexpr std::string_view build_timestamp = "2026-03-31 16:56:10 UTC";
constexpr std::string_view cmake_version = "3.28.3";
constexpr std::string_view library_type = "Static"; // Static or Shared

} // namespace dummy_lib_info
