#include "secure_ops/secure_ops.h"

#include <cstddef>
#include <cstdint>

namespace secure_ops {

// NOLINTNEXTLINE(readability-identifier-length)
static inline uint64_t rotl(uint64_t val, unsigned rot) noexcept {
    return (val << rot) | (val >> ((sizeof(val) * 8) - rot));
}

uint64_t process_input(const uint8_t* data, size_t size) noexcept {
    uint64_t hash = 14695981039346656037ULL; // FNV offset basis
    for (size_t i = 0; i < size; ++i) {
        hash ^= static_cast<uint64_t>(data[i]);
        hash *= 1099511628211ULL;
        auto rot = static_cast<unsigned>(data[i] % 13);
        hash = rotl(hash, rot);
    }
    hash ^= static_cast<uint64_t>(size);
    hash ^= (hash >> 33);
    hash *= 0xff51afd7ed558ccdULL;
    hash ^= (hash >> 33);
    hash *= 0xc4ceb9fe1a85ec53ULL;
    hash ^= (hash >> 33);
    return hash;
}

} // namespace secure_ops
