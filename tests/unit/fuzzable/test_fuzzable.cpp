#include <array>
#include <gtest/gtest.h>

#include "fuzzable/fuzzable.h"

TEST(FuzzableTest, ProcessSimpleSum) {
    // type 3 -> checksum
    const std::array<uint8_t, 5> kData{{0x03, 1, 2, 3, 4}};
    const auto result = fuzzable::process_input(kData.data(), kData.size());
    EXPECT_TRUE(result.ok);
    EXPECT_EQ(result.value, 1 + 2 + 3 + 4);
}

TEST(FuzzableTest, ParseInteger) {
    const std::array<uint8_t, 5> kPayload{
        {0x01, 0x00, 0x02, '4', '2'}}; // type=1 len=2 payload="42"
    const auto result = fuzzable::process_input(kPayload.data(), kPayload.size());
    EXPECT_TRUE(result.ok);
    EXPECT_EQ(result.value, 42);
}
