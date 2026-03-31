// tests/unit/dummy_lib/greet_test.cpp
#include "dummy_lib/greet.h"

#include <gtest/gtest.h>
#include <string>

#include "ProjectInfo.h" // BuildInfo.h + FeatureFlags.h + BuildInfoHelper.h

// ── dummy_lib functional tests ───────────────────────────────────────────────

TEST(DummyLibTest, GetGreetingIsNotEmpty) { EXPECT_FALSE(dummy_lib::get_greeting().empty()); }

TEST(DummyLibTest, GetGreetingContainsExpectedText) {
    EXPECT_NE(dummy_lib::get_greeting().find("Dummy"), std::string::npos);
}

// ── BuildInfo tests ──────────────────────────────────────────────────────────

TEST(BuildInfoTest, ProjectNameNotEmpty) { EXPECT_FALSE(dummy_lib_info::project_name.empty()); }

TEST(BuildInfoTest, ProjectVersionNotEmpty) {
    EXPECT_FALSE(dummy_lib_info::project_version.empty());
}

TEST(BuildInfoTest, CompilerIdNotEmpty) { EXPECT_FALSE(dummy_lib_info::compiler_id.empty()); }

TEST(BuildInfoTest, ArchitectureKnown) {
    const auto& arch = dummy_lib_info::architecture;
    EXPECT_TRUE(arch == "x64" || arch == "x86" || arch == "arm"); // NOLINT
}

TEST(BuildInfoTest, LibraryTypeKnown) {
    const auto& library_type = dummy_lib_info::library_type;
    EXPECT_TRUE(library_type == "Static" || library_type == "Shared" ||
                library_type == "Executable"); // NOLINT
}

TEST(BuildInfoTest, BuildTypeNotEmpty) { EXPECT_FALSE(dummy_lib_info::build_type.empty()); }

TEST(BuildInfoTest, TimestampNotEmpty) { EXPECT_FALSE(dummy_lib_info::build_timestamp.empty()); }

TEST(BuildInfoTest, GitHashNotEmpty) { EXPECT_FALSE(dummy_lib_info::git_hash.empty()); }

TEST(BuildInfoTest, VersionLineContainsVersion) {
    const std::string VERSION_LINE = BUILD_INFO_VERSION_LINE(dummy_lib_info);
    EXPECT_NE(VERSION_LINE.find(std::string(dummy_lib_info::project_version)), std::string::npos);
}

// ── FeatureFlags tests ───────────────────────────────────────────────────────

TEST(FeatureFlagsTest, ArrayNonEmpty) { EXPECT_FALSE(project_features::features.empty()); }

TEST(FeatureFlagsTest, AllNamesNonEmpty) {
    for (const auto& feature : project_features::features) {
        EXPECT_FALSE(feature.name.empty()) << "Feature with empty name found";
    }
}

TEST(FeatureFlagsTest, GTestFlagIsTrue) {
    EXPECT_EQ(FEATURE_GTEST, 1);
    bool found = false;
    for (const auto& feature : project_features::features) {
        if (feature.name == "gtest") {
            EXPECT_TRUE(feature.enabled);
            found = true;
        }
    }
    EXPECT_TRUE(found) << "'gtest' missing from features array";
}

TEST(FeatureFlagsTest, SharedLibsMacroMatchesLibraryType) {
    bool shared = (dummy_lib_info::library_type == "Shared");
    EXPECT_EQ(bool(PROJECT_SHARED_LIBS), shared);
}
