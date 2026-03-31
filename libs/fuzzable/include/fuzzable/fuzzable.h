// libs/fuzzable/include/fuzzable/fuzzable.h
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace fuzzable {

struct Result {
    bool ok;
    int value;
    std::string msg;
};

// Process arbitrary input buffer. Designed to exercise parsing and small
// algorithms without using exceptions (noexcept) so it is compatible with
// hardened/EXTREME profiles that disable exceptions.
Result process_input(const uint8_t* data, size_t size) noexcept;

} // namespace fuzzable
