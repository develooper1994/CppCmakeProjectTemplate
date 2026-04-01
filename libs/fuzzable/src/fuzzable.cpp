// libs/fuzzable/src/fuzzable.cpp
#include "fuzzable/fuzzable.h"

#include <cctype>
#include <climits>
#include <cstdint>
#include <string>

namespace fuzzable {

static bool parse_int_from_bytes(const uint8_t* buf, size_t len, int& out) noexcept {
    if (len == 0 || buf == nullptr) {
        return false;
    }

    long long accum = 0;
    bool negative = false;
    size_t idx = 0;
    char first_ch = static_cast<char>(buf[0]);
    if (first_ch == '+' || first_ch == '-') {
        negative = (first_ch == '-');
        idx = 1;
        if (len == 1) {
            return false;
        }
    }

    for (; idx < len; ++idx) {
        char cur_ch = static_cast<char>(buf[idx]);
        if (std::isdigit(static_cast<unsigned char>(cur_ch)) == 0) {
            return false;
        }
        accum = accum * 10 + (cur_ch - '0');
        if (accum > INT32_MAX) {
            return false;
        }
    }

    out = negative ? -static_cast<int>(accum) : static_cast<int>(accum);
    return true;
}

// cppcheck-suppress unusedFunction
[[maybe_unused]] Result process_input(const uint8_t* data, size_t size) noexcept {
    Result result{false, 0, std::string()};
    if (data == nullptr || size == 0) {
        result.msg = "empty";
        return result;
    }

    const uint8_t MESSAGE_TYPE = data[0];

    // Type 1: simple integer parser from payload
    if (MESSAGE_TYPE == 0x01) {
        if (size < 3) {
            result.msg = "short1";
            return result;
        }
        auto payload_len = static_cast<uint16_t>((static_cast<uint32_t>(data[1]) << 8) |
                                                 static_cast<uint32_t>(data[2]));
        if (size < static_cast<size_t>(3 + payload_len)) {
            result.msg = "len-mismatch";
            return result;
        }
        const uint8_t* payload_ptr = &data[3];
        int parsed = 0;
        if (parse_int_from_bytes(payload_ptr, payload_len, parsed)) {
            result.ok = true;
            result.value = parsed;
            result.msg = "ok-int";
            return result;
        }
        result.msg = "bad-int";
        return result;
    }

    // Type 2: simple expression a+b where a and b are small integers
    if (MESSAGE_TYPE == 0x02) {
        const uint8_t* payload_ptr = &data[1];
        const size_t PAYLOAD_LEN = size - 1;
        for (size_t idx = 0; idx < PAYLOAD_LEN; ++idx) {
            if (static_cast<char>(payload_ptr[idx]) == '+') {
                int left = 0;
                int right = 0;
                if (parse_int_from_bytes(payload_ptr, idx, left) &&
                    parse_int_from_bytes(payload_ptr + idx + 1, PAYLOAD_LEN - idx - 1, right)) {
                    result.ok = true;
                    result.value = left + right;
                    result.msg = "expr";
                    return result;
                }
                break;
            }
        }
        result.msg = "noexpr";
        return result;
    }

    // Type 3: checksum of payload
    if (MESSAGE_TYPE == 0x03) {
        uint32_t sum = 0U;
        for (size_t idx = 1; idx < size; ++idx) {
            sum += static_cast<uint32_t>(data[idx]);
        }
        result.ok = true;
        result.value = static_cast<int>(sum & 0xffffffffU);
        result.msg = "sum";
        return result;
    }

    result.msg = "unknown-type";
    return result;
}

} // namespace fuzzable
