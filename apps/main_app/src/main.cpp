#include <iostream>
#include "dummy_lib/greet.h"
#include "BuildInfo.h"

int main() {
    std::cout << build_info::project_name << " v" << build_info::project_version << "\n";
    std::cout << "Branch: " << build_info::git_branch << " Hash: " << build_info::git_hash << "\n";
    std::cout << "Compiler: " << build_info::compiler_id << " v" << build_info::compiler_version << "\n";
    std::cout << "Architecture: " << build_info::architecture << "\n";
    std::cout << "Built: " << build_info::build_timestamp << "\n";
    std::cout << "Library Type: " << build_info::library_type << "\n";
    std::cout << "CMake: v" << build_info::cmake_version << "\n";
    std::cout << dummy_lib::get_greeting() << "\n";
    return 0;
}
