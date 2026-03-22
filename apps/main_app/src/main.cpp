#include <iostream>
#include "dummy_lib/greet.h"
#include "ProjectInfo.h"   // BuildInfo.h + FeatureFlags.h + BuildInfoHelper.h

int main()
{
    // Print all build-time info using the convenience macro
    BUILD_INFO_PRINT_ALL(std::cout, main_app_info);

    std::cout << dummy_lib::get_greeting() << "\n";
    return 0;
}
