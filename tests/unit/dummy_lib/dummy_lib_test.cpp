// tests/unit/dummy_lib/dummy_lib_test.cpp
#include "dummy_lib/dummy_lib.h"

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

// ── Performance metadata tests ───────────────────────────────────────────────

TEST(PerfMetaTest, LtoEnabledIsBool) {
    // Just verifying the field exists and is a compile-time bool
    EXPECT_TRUE(dummy_lib_info::lto_enabled == true || dummy_lib_info::lto_enabled == false);
}

TEST(PerfMetaTest, PgoModeIsKnownValue) {
    const auto& mode = dummy_lib_info::pgo_mode;
    EXPECT_TRUE(mode == "off" || mode == "generate" || mode == "use")
        << "Unexpected pgo_mode: " << mode;
}

TEST(PerfMetaTest, BuildCacheIsKnownValue) {
    const auto& cache = dummy_lib_info::build_cache;
    EXPECT_TRUE(cache == "none" || cache == "ccache" || cache == "sccache")
        << "Unexpected build_cache: " << cache;
}

TEST(PerfMetaTest, SummaryStringContainsPerformanceSection) {
    // NOLINTBEGIN(readability-identifier-naming)
    const std::string summary_text = BUILD_INFO_SUMMARY_STRING(dummy_lib_info);
    EXPECT_NE(summary_text.find("Performance"), std::string::npos)
        << "Summary missing Performance section";
    EXPECT_NE(summary_text.find("LTO"), std::string::npos) << "Summary missing LTO row";
    EXPECT_NE(summary_text.find("PGO"), std::string::npos) << "Summary missing PGO row";
    // NOLINTEND(readability-identifier-naming)
}

TEST(PerfMetaTest, LtoFlagConsistentWithFeatureFlags) {
    // FEATURE_LTO and lto_enabled must agree
    bool feature_lto = (FEATURE_LTO == 1);
    EXPECT_EQ(feature_lto, dummy_lib_info::lto_enabled);
}
