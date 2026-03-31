#include "dummy_lib/greet.h"
#include <cstddef>
#include <cstdint>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    // Trivial harness: call library API to exercise codepaths.
    (void)data; (void)size;
    dummy_lib::get_greeting();
    return 0;
}
