#pragma once

#include <string>
#include "dummy_lib/dummy_lib_export.h"

namespace dummy_lib {

// Use DUMMY_LIB_EXPORT for cross-platform visibility
DUMMY_LIB_EXPORT std::string get_greeting();

} // namespace dummy_lib
