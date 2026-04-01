#include <gtest/gtest.h>
#include "secure_ops/secure_ops.h"

#include <array>
#include <cstring>
#include <vector>

namespace {

TEST(SecureOps, NullDataZeroSize) {
    // Must not crash with null pointer and zero size
    auto result = secure_ops::process_input(nullptr, 0);
    // Just verify it returns a deterministic value
    EXPECT_EQ(result, secure_ops::process_input(nullptr, 0));
}

TEST(SecureOps, EmptyInput) {
    const uint8_t data = 0;
    auto result = secure_ops::process_input(&data, 0);
    EXPECT_EQ(result, secure_ops::process_input(nullptr, 0));
}

TEST(SecureOps, Determinism) {
    // Same input must always produce the same output
    const std::array<uint8_t, 8> data = {0x01, 0x02, 0x03, 0x04,
                                          0x05, 0x06, 0x07, 0x08};
    auto a = secure_ops::process_input(data.data(), data.size());
    auto b = secure_ops::process_input(data.data(), data.size());
    EXPECT_EQ(a, b);
}

TEST(SecureOps, DifferentInputsDifferentOutputs) {
    const std::array<uint8_t, 4> data_a = {0x01, 0x02, 0x03, 0x04};
    const std::array<uint8_t, 4> data_b = {0x04, 0x03, 0x02, 0x01};
    auto a = secure_ops::process_input(data_a.data(), data_a.size());
    auto b = secure_ops::process_input(data_b.data(), data_b.size());
    EXPECT_NE(a, b);
}

TEST(SecureOps, AvalancheEffect) {
    // Flipping a single bit should produce a significantly different hash
    std::array<uint8_t, 16> data = {};
    data.fill(0xAA);

    auto base_hash = secure_ops::process_input(data.data(), data.size());

    // Flip one bit
    data[7] ^= 0x01;
    auto flipped_hash = secure_ops::process_input(data.data(), data.size());

    EXPECT_NE(base_hash, flipped_hash);

    // Count differing bits (expect good avalanche: ~50% of 64 bits differ)
    uint64_t diff = base_hash ^ flipped_hash;
    int bit_diffs = 0;
    while (diff) {
        bit_diffs += static_cast<int>(diff & 1);
        diff >>= 1;
    }
    // At least 10 bits should differ for decent avalanche
    EXPECT_GE(bit_diffs, 10);
}

TEST(SecureOps, VariousSizes) {
    // Test with sizes 1, 8, 256 — must not crash or hang
    for (size_t sz : {1u, 8u, 256u, 1024u}) {
        std::vector<uint8_t> data(sz, 0x42);
        auto result = secure_ops::process_input(data.data(), data.size());
        // Just verify non-zero (extremely unlikely for a good hash to be 0)
        EXPECT_NE(result, 0u);
    }
}

TEST(SecureOps, SizeAffectsOutput) {
    // Same content but different sizes should produce different hashes
    std::vector<uint8_t> short_data(4, 0xFF);
    std::vector<uint8_t> long_data(8, 0xFF);
    auto a = secure_ops::process_input(short_data.data(), short_data.size());
    auto b = secure_ops::process_input(long_data.data(), long_data.size());
    EXPECT_NE(a, b);
}

} // namespace
