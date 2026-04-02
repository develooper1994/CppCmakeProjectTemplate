#include <iostream>

#include "ProjectInfo.h" // BuildInfo.h + FeatureFlags.h + BuildInfoHelper.h
#include "dummy_lib/dummy_lib.h"

int main() {
    // Print all build-time info using the convenience macro
    BUILD_INFO_PRINT_ALL(std::cout, main_app_info);

    std::cout << dummy_lib::get_greeting() << "\n";
    return 0;
}
