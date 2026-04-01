/**
 * bench_greet.cpp — Google Benchmark example for dummy_lib.
 *
 * Demonstrates:
 *   • Basic benchmark registration
 *   • Performance annotations: [[likely]], [[unlikely]], [[nodiscard]]
 *   • Compiler hints: __attribute__((hot)), __attribute__((pure))
 *   • Fixture-based benchmarks
 *   • Template benchmarks with different input sizes
 *
 * Build: cmake -DENABLE_BENCHMARKS=ON ...
 * Run:   ./build/<preset>/benchmarks/bench_greet
 *        ./build/<preset>/benchmarks/bench_greet --benchmark_filter=BM_Greet
 *        ./build/<preset>/benchmarks/bench_greet --benchmark_format=json
 */

#include <benchmark/benchmark.h>
#include <dummy_lib/greet.h>

#include <algorithm>
#include <array>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

// ---------------------------------------------------------------------------
// Cross-platform performance annotation helpers
// ---------------------------------------------------------------------------
#ifdef __GNUC__
#  define ATTR_HOT         __attribute__((hot))
#  define ATTR_COLD        __attribute__((cold))
#  define ATTR_PURE        __attribute__((pure))
#  define ATTR_NOINLINE    __attribute__((noinline))
#else
#  define ATTR_HOT
#  define ATTR_COLD
#  define ATTR_PURE
#  define ATTR_NOINLINE
#endif

// ---------------------------------------------------------------------------
// Helper functions — show annotation patterns
// ---------------------------------------------------------------------------

/// Annotated as "hot" — optimizer increases inlining aggressiveness.
ATTR_HOT static std::string fast_greet(std::string_view name) {
    std::string result;
    result.reserve(name.size() + 8);
    result = "Hello, ";
    result += name;
    result += '!';
    return result;
}

/// Annotated as "noinline" — forces function call overhead, useful for measuring
/// the actual call site cost rather than inlined code.
ATTR_NOINLINE static std::string noinline_greet(std::string_view name) {
    return std::string{"Hello, "} + std::string{name} + "!";
}

/// [[nodiscard]] ensures callers don't accidentally discard the return value.
[[nodiscard]] ATTR_PURE static bool is_valid_name(std::string_view name) noexcept {
    return !name.empty() && name.size() <= 256;
}

// ---------------------------------------------------------------------------
// Basic benchmarks
// ---------------------------------------------------------------------------

/// Baseline: use the public library API.
static void BM_Greet_LibraryCall(benchmark::State& state) {
    for (auto _ : state) {
        auto result = dummy_lib::greet("World");
        benchmark::DoNotOptimize(result);
        benchmark::ClobberMemory();
    }
}
BENCHMARK(BM_Greet_LibraryCall);

/// Hot-annotated fast path.
static void BM_Greet_HotPath(benchmark::State& state) {
    for (auto _ : state) {
        auto result = fast_greet("World");
        benchmark::DoNotOptimize(result);
        benchmark::ClobberMemory();
    }
}
BENCHMARK(BM_Greet_HotPath);

/// NoInline path — measures function-call overhead.
static void BM_Greet_Noinline(benchmark::State& state) {
    for (auto _ : state) {
        auto result = noinline_greet("World");
        benchmark::DoNotOptimize(result);
        benchmark::ClobberMemory();
    }
}
BENCHMARK(BM_Greet_Noinline);

// ---------------------------------------------------------------------------
// Template benchmark — varies name length to explore scaling
// ---------------------------------------------------------------------------

template <std::size_t N>
static void BM_Greet_NameSize(benchmark::State& state) {
    std::string name(N, 'x');
    for (auto _ : state) {
        auto result = fast_greet(name);
        benchmark::DoNotOptimize(result);
        benchmark::ClobberMemory();
    }
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * static_cast<long long>(N));
}

BENCHMARK_TEMPLATE(BM_Greet_NameSize, 1);
BENCHMARK_TEMPLATE(BM_Greet_NameSize, 8);
BENCHMARK_TEMPLATE(BM_Greet_NameSize, 64);
BENCHMARK_TEMPLATE(BM_Greet_NameSize, 256);

// ---------------------------------------------------------------------------
// [[likely]] / [[unlikely]] branch prediction hints benchmark
// ---------------------------------------------------------------------------

static void BM_BranchPrediction_Likely(benchmark::State& state) {
    const std::vector<std::string_view> names = {"Alice", "Bob", "Carol", "Dave", "Eve"};
    std::size_t idx = 0;
    for (auto _ : state) {
        std::string_view name = names[idx % names.size()];
        ++idx;
        // [[likely]]: optimizer assumes this branch is taken most of the time
        if (is_valid_name(name)) [[likely]] {
            auto result = fast_greet(name);
            benchmark::DoNotOptimize(result);
        }
    }
}
BENCHMARK(BM_BranchPrediction_Likely);

static void BM_BranchPrediction_Unlikely(benchmark::State& state) {
    const std::vector<std::string_view> names = {"Alice", "Bob", "Carol", "Dave", "Eve"};
    std::size_t idx = 0;
    std::string_view empty_name;
    for (auto _ : state) {
        std::string_view name = (idx % 100 == 0) ? empty_name : names[idx % names.size()];
        ++idx;
        // [[unlikely]]: optimizer knows error branch is rarely taken
        if (!is_valid_name(name)) [[unlikely]] {
            benchmark::DoNotOptimize(name.size());
        } else {
            auto result = fast_greet(name);
            benchmark::DoNotOptimize(result);
        }
    }
}
BENCHMARK(BM_BranchPrediction_Unlikely);

// ---------------------------------------------------------------------------
// Fixture-based benchmark — setup/teardown per range
// ---------------------------------------------------------------------------

class GreetFixture : public benchmark::Fixture {
public:
    void SetUp(const benchmark::State& state) override {
        names_.resize(static_cast<std::size_t>(state.range(0)));
        for (std::size_t i = 0; i < names_.size(); ++i) {
            names_[i] = "User" + std::to_string(i);
        }
    }

    void TearDown(const benchmark::State& /*state*/) override {
        names_.clear();
    }

protected:
    std::vector<std::string> names_;
};

BENCHMARK_DEFINE_F(GreetFixture, BM_BatchGreet)(benchmark::State& state) {
    for (auto _ : state) {
        for (const auto& name : names_) {
            auto result = fast_greet(name);
            benchmark::DoNotOptimize(result);
        }
        benchmark::ClobberMemory();
    }
    state.SetItemsProcessed(state.iterations() * static_cast<long long>(names_.size()));
}

BENCHMARK_REGISTER_F(GreetFixture, BM_BatchGreet)->Range(8, 1024);

// ---------------------------------------------------------------------------
// Memory allocation patterns — stack vs heap strings
// ---------------------------------------------------------------------------

static void BM_StringAlloc_Heap(benchmark::State& state) {
    for (auto _ : state) {
        std::string s = "Hello, World!";
        benchmark::DoNotOptimize(s);
        benchmark::ClobberMemory();
    }
}
BENCHMARK(BM_StringAlloc_Heap);

static void BM_StringAlloc_StringView(benchmark::State& state) {
    for (auto _ : state) {
        constexpr std::string_view sv = "Hello, World!";
        benchmark::DoNotOptimize(sv);
    }
}
BENCHMARK(BM_StringAlloc_StringView);

// Main is provided by benchmark::benchmark_main (via target_apply_benchmark_options)
