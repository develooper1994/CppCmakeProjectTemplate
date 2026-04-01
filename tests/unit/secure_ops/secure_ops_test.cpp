#include "secure_ops/secure_ops.h"

#include <array>
#include <cstring>
#include <gtest/gtest.h>
#include <vector>

namespace {

TEST(SecureOps, NullDataZeroSize) {
    // Must not crash with null pointer and zero size
    auto result = secure_ops::process_input(nullptr, 0);
    // Just verify it returns a deterministic value
    EXPECT_EQ(result, secure_ops::process_input(nullptr, 0));
}

TEST(SecureOps, EmptyInput) {
    const uint8_t kDummy = 0;  // NOLINT(readability-identifier-naming)
    auto result = secure_ops::process_input(&kDummy, 0);
    EXPECT_EQ(result, secure_ops::process_input(nullptr, 0));
}

TEST(SecureOps, Determinism) {
    // Same input must always produce the same output
    const std::array<uint8_t, 8> kInput = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};  // NOLINT(readability-identifier-naming)
    auto hash_first = secure_ops::process_input(kInput.data(), kInput.size());
    auto hash_second = secure_ops::process_input(kInput.data(), kInput.size());
    EXPECT_EQ(hash_first, hash_second);
}

TEST(SecureOps, DifferentInputsDifferentOutputs) {
    const std::array<uint8_t, 4> kInputA = {0x01, 0x02, 0x03, 0x04};  // NOLINT(readability-identifier-naming)
    const std::array<uint8_t, 4> kInputB = {0x04, 0x03, 0x02, 0x01};  // NOLINT(readability-identifier-naming)
    auto hash_a = secure_ops::process_input(kInputA.data(), kInputA.size());
    auto hash_b = secure_ops::process_input(kInputB.data(), kInputB.size());
    EXPECT_NE(hash_a, hash_b);
}

TEST(SecureOps, AvalancheEffect) {
    // Flipping a single bit should produce a significantly different hash
    std::array<uint8_t, 16> input_buf = {};
    input_buf.fill(0xAA);

    auto base_hash = secure_ops::process_input(input_buf.data(), input_buf.size());

    // Flip one bit
    input_buf[7] ^= 0x01;
    auto flipped_hash = secure_ops::process_input(input_buf.data(), input_buf.size());

    EXPECT_NE(base_hash, flipped_hash);

    // Count differing bits (expect good avalanche: ~50% of 64 bits differ)
    uint64_t diff = base_hash ^ flipped_hash;
    int bit_diffs = 0;
    while (diff != 0U) {
        bit_diffs += static_cast<int>(diff & 1U);
        diff >>= 1U;
    }
    // At least 10 bits should differ for decent avalanche
    EXPECT_GE(bit_diffs, 10);
}

TEST(SecureOps, VariousSizes) {
    // Test with sizes 1, 8, 256 — must not crash or hang
    for (size_t size : {1U, 8U, 256U, 1024U}) {
        std::vector<uint8_t> input_vec(size, 0x42);
        auto result = secure_ops::process_input(input_vec.data(), input_vec.size());
        // Just verify non-zero (extremely unlikely for a good hash to be 0)
        EXPECT_NE(result, 0U);
    }
}

TEST(SecureOps, SizeAffectsOutput) {
    // Same content but different sizes should produce different hashes
    std::vector<uint8_t> short_vec(4, 0xFF);
    std::vector<uint8_t> long_vec(8, 0xFF);
    auto hash_short = secure_ops::process_input(short_vec.data(), short_vec.size());
    auto hash_long = secure_ops::process_input(long_vec.data(), long_vec.size());
    EXPECT_NE(hash_short, hash_long);
}

} // namespace
