#include <cstddef>
#include <cstdint>

#include "fuzzable/fuzzable.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    // Call into the fuzzable library to exercise parsing and branches.
    auto result = fuzzable::process_input(data, size);
    // Lightweight checks to keep fuzzer informed of interesting results.
    if (result.ok && result.value == 0xdeadbeef) {
        // Do nothing — just a reachable guard for potential interesting states
        (void)result.msg;
    }
    return 0;
}
