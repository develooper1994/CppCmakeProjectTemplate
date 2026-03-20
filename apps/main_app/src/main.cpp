#include <iostream>
#include "dummy_lib/greet.h"
#include "BuildInfo.h"

int main() {
    std::cout << build_info::project_name << " v" << build_info::project_version << "\n";
    std::cout << "Branch: " << build_info::git_branch << " Hash: " << build_info::git_hash << "\n";
    std::cout << dummy_lib::get_greeting() << "\n";
    return 0;
}
