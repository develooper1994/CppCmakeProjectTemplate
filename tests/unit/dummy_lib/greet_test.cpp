// tests/unit/dummy_lib/greet_test.cpp

#include <gtest/gtest.h>
#include "dummy_lib/greet.h"
#include "BuildInfo.h"
#include "BuildInfoHelper.h"
#include "FeatureFlags.h"

#include <iostream>
#include <string>

// ── Dump all build-time info before any test runs ───────────────────────────

class BuildInfoEnvironment : public ::testing::Environment {
public:
    void SetUp() override {
        BUILD_INFO_PRINT_ALL(std::cout, dummy_lib_info);
        std::cout << std::flush;
    }
};

static ::testing::Environment* const _build_env =
    ::testing::AddGlobalTestEnvironment(new BuildInfoEnvironment);

// ── Existing tests ───────────────────────────────────────────────────────────

TEST(DummyLibTest, GetGreetingIsNotEmpty) {
    EXPECT_FALSE(dummy_lib::get_greeting().empty());
}

TEST(DummyLibTest, GetGreetingContainsExpectedText) {
    EXPECT_NE(dummy_lib::get_greeting().find("Dummy"), std::string::npos);
}

// ── BuildInfo tests ──────────────────────────────────────────────────────────

TEST(BuildInfoTest, ProjectNameNotEmpty) {
    EXPECT_FALSE(dummy_lib_info::project_name.empty());
}

TEST(BuildInfoTest, ProjectVersionNotEmpty) {
    EXPECT_FALSE(dummy_lib_info::project_version.empty());
}

TEST(BuildInfoTest, CompilerIdNotEmpty) {
    EXPECT_FALSE(dummy_lib_info::compiler_id.empty());
}

TEST(BuildInfoTest, ArchitectureKnown) {
    const auto& arch = dummy_lib_info::architecture;
    EXPECT_TRUE(arch == "x64" || arch == "x86" || arch == "arm");
}

TEST(BuildInfoTest, LibraryTypeKnown) {
    const auto& lt = dummy_lib_info::library_type;
    EXPECT_TRUE(lt == "Static" || lt == "Shared" || lt == "Executable");
}

TEST(BuildInfoTest, BuildTypeNotEmpty) {
    EXPECT_FALSE(dummy_lib_info::build_type.empty());
}

TEST(BuildInfoTest, TimestampNotEmpty) {
    EXPECT_FALSE(dummy_lib_info::build_timestamp.empty());
}

TEST(BuildInfoTest, GitHashNotEmpty) {
    EXPECT_FALSE(dummy_lib_info::git_hash.empty());
}

TEST(BuildInfoTest, VersionLineContainsVersion) {
    const std::string vl = BUILD_INFO_VERSION_LINE(dummy_lib_info);
    EXPECT_NE(vl.find(std::string(dummy_lib_info::project_version)), std::string::npos);
}

// ── FeatureFlags tests ───────────────────────────────────────────────────────

TEST(FeatureFlagsTest, ArrayNonEmpty) {
    EXPECT_FALSE(project_features::features.empty());
}

TEST(FeatureFlagsTest, AllNamesNonEmpty) {
    for (const auto& f : project_features::features)
        EXPECT_FALSE(f.name.empty()) << "Feature with empty name found";
}

TEST(FeatureFlagsTest, GTestFlagIsTrue) {
    // We ARE running inside GTest, so FEATURE_GTEST must be 1
    EXPECT_EQ(FEATURE_GTEST, 1);
    bool found = false;
    for (const auto& f : project_features::features) {
        if (f.name == "gtest") {
            EXPECT_TRUE(f.enabled);
            found = true;
        }
    }
    EXPECT_TRUE(found) << "'gtest' entry missing from features array";
}

TEST(FeatureFlagsTest, SharedLibsMacroMatchesLibraryType) {
    // dummy_lib is a library (Static or Shared), not Executable
    bool shared = (dummy_lib_info::library_type == "Shared");
    EXPECT_EQ(bool(PROJECT_SHARED_LIBS), shared);
}
