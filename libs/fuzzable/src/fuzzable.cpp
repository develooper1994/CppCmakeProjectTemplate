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
    char ch = static_cast<char>(buf[0]);
    if (ch == '+' || ch == '-') {
        negative = (ch == '-');
        idx = 1;
        if (len == 1) {
            return false;
        }
    }

    for (; idx < len; ++idx) {
        char c = static_cast<char>(buf[idx]);
        if (!std::isdigit(static_cast<unsigned char>(c))) {
            return false;
        }
        accum = accum * 10 + (c - '0');
        if (accum > INT32_MAX) {
            return false;
        }
    }

    out = negative ? -static_cast<int>(accum) : static_cast<int>(accum);
    return true;
}

Result process_input(const uint8_t* data, size_t size) noexcept {
    Result result{false, 0, std::string()};
    if (data == nullptr || size == 0) {
        result.msg = "empty";
        return result;
    }

    const uint8_t message_type = data[0];

    // Type 1: simple integer parser from payload
    if (message_type == 0x01) {
        if (size < 3) {
            result.msg = "short1";
            return result;
        }
        const uint16_t payload_len = (static_cast<uint16_t>(data[1]) << 8) | data[2];
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
    if (message_type == 0x02) {
        const uint8_t* payload_ptr = &data[1];
        const size_t payload_len = size - 1;
        for (size_t idx = 0; idx < payload_len; ++idx) {
            if (static_cast<char>(payload_ptr[idx]) == '+') {
                int left = 0;
                int right = 0;
                if (parse_int_from_bytes(payload_ptr, idx, left) &&
                    parse_int_from_bytes(payload_ptr + idx + 1, payload_len - idx - 1, right)) {
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
    if (message_type == 0x03) {
        uint32_t sum = 0u;
        for (size_t idx = 1; idx < size; ++idx) {
            sum += static_cast<uint32_t>(data[idx]);
        }
        result.ok = true;
        result.value = static_cast<int>(sum & 0xffffffffu);
        result.msg = "sum";
        return result;
    }

    result.msg = "unknown-type";
    return result;
}

} // namespace fuzzable
