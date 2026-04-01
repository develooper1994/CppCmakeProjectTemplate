#include <array>
#include <gtest/gtest.h>

#include "fuzzable/fuzzable.h"

TEST(FuzzableTest, ProcessSimpleSum) {
    // type 3 -> checksum
    const std::array<uint8_t, 5> K_DATA{{0x03, 1, 2, 3, 4}};
    const auto RESULT = fuzzable::process_input(K_DATA.data(), K_DATA.size());
    EXPECT_TRUE(RESULT.ok);
    EXPECT_EQ(RESULT.value, 1 + 2 + 3 + 4);
}

TEST(FuzzableTest, ParseInteger) {
    const std::array<uint8_t, 5> K_PAYLOAD{
        {0x01, 0x00, 0x02, '4', '2'}}; // type=1 len=2 payload="42"
    const auto RESULT = fuzzable::process_input(K_PAYLOAD.data(), K_PAYLOAD.size());
    EXPECT_TRUE(RESULT.ok);
    EXPECT_EQ(RESULT.value, 42);
}
