#include <iostream>
#include "dummy_lib/greet.h"
#include "BuildInfo.h"
#include "FeatureFlags.h"

int main() {
    std::cout << main_app_info::project_name << " v" << main_app_info::project_version << "\n";
    std::cout << "Branch: "       << main_app_info::git_branch       << " Hash: " << main_app_info::git_hash << "\n";
    std::cout << "Compiler: "     << main_app_info::compiler_id      << " v" << main_app_info::compiler_version << "\n";
    std::cout << "Architecture: " << main_app_info::architecture      << "\n";
    std::cout << "Built: "        << main_app_info::build_timestamp   << "\n";
    std::cout << "Library Type: " << main_app_info::library_type      << "\n";
    std::cout << "CMake: v"       << main_app_info::cmake_version     << "\n";

    // Active build features
    std::cout << "\nBuild features:\n";
    for (const auto& f : project_features::features)
        std::cout << "  " << (f.enabled ? "[x]" : "[ ]") << " " << f.name << "\n";

    std::cout << "\n" << dummy_lib::get_greeting() << "\n";
    return 0;
}
