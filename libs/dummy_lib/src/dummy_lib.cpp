#include "dummy_lib/dummy_lib.h"

namespace dummy_lib {
// Suppress cppcheck warning about unusedFunction for this public API
// cppcheck-suppress unusedFunction
std::string get_greeting() {
    return "Hello from Dummy Library!";
}

} // namespace dummy_lib
