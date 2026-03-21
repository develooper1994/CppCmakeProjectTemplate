#include <gtest/gtest.h>
#include "dummy_lib/greet.h"

TEST(DummyLibTest, GreetReturnsNonEmptyString) {
    EXPECT_FALSE(dummy_lib::get_greeting().empty());
}

TEST(DummyLibTest, GreetContainsHello) {
    EXPECT_NE(dummy_lib::get_greeting().find("Hello"), std::string::npos);
}
