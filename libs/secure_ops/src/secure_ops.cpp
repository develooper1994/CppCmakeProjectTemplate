#include "secure_ops/secure_ops.h"

#include <cstddef>
#include <cstdint>

namespace secure_ops {

static inline uint64_t rotl(uint64_t x, unsigned r) noexcept {
    return (x << r) | (x >> ((sizeof(x) * 8) - r));
}

uint64_t process_input(const uint8_t* data, size_t size) noexcept {
    uint64_t h = 14695981039346656037ULL; // FNV offset basis
    for (size_t i = 0; i < size; ++i) {
        h ^= static_cast<uint64_t>(data[i]);
        h *= 1099511628211ULL;
        unsigned r = static_cast<unsigned>(data[i] % 13);
        h = rotl(h, r);
    }
    h ^= static_cast<uint64_t>(size);
    h ^= (h >> 33);
    h *= 0xff51afd7ed558ccdULL;
    h ^= (h >> 33);
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= (h >> 33);
    return h;
}

} // namespace secure_ops
