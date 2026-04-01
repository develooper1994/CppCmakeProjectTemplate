/**
 * bench_greet.cpp — Google Benchmark: compute-intensive math benchmarks.
 *
 * Demonstrates real performance differences between:
 *   • Sieve of Eratosthenes  (cache-friendly array access)
 *   • Monte Carlo π          (branch-heavy random simulation)
 *   • Matrix multiply        (O(N³) FLOPS, cache-hostile vs tiled)
 *   • Fibonacci (recursive)  (exponential — shows LTO/inlining gain)
 *   • Newton–Raphson √       (FPU-bound convergence loop)
 *
 * Build variants to compare (requires -DENABLE_BENCHMARKS=ON):
 *   Debug   : cmake --preset gcc-debug-static-x86_64
 *   Release : cmake --preset gcc-release-static-x86_64
 *   LTO     : cmake --preset gcc-release-static-x86_64 -DENABLE_LTO=ON
 *
 * Run:
 *   ./build/<preset>/benchmarks/bench_math
 *   ./build/<preset>/benchmarks/bench_math --benchmark_filter=BM_Sieve
 *   ./build/<preset>/benchmarks/bench_math --benchmark_format=json \
 *       --benchmark_out=build_logs/bench_results.json
 */

#include <benchmark/benchmark.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <random>
#include <vector>

// ── compiler hints ──────────────────────────────────────────────────────────
#ifdef __GNUC__
#  define ATTR_HOT      __attribute__((hot))
#  define ATTR_NOINLINE __attribute__((noinline))
#else
#  define ATTR_HOT
#  define ATTR_NOINLINE
#endif

// ===========================================================================
// 1. Sieve of Eratosthenes
//    Cache-friendly sequential bit operations.
//    Measures: memory bandwidth, branch predictor, auto-vectorization.
// ===========================================================================

ATTR_HOT static std::vector<bool> sieve(std::size_t limit) {
    std::vector<bool> is_prime(limit + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (std::size_t i = 2; i * i <= limit; ++i) {
        if (is_prime[i]) {
            for (std::size_t j = i * i; j <= limit; j += i)
                is_prime[j] = false;
        }
    }
    return is_prime;
}

static void BM_Sieve_10k(benchmark::State& state) {
    for (auto _ : state) {
        auto result = sieve(10'000);
        benchmark::DoNotOptimize(result);
    }
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 10'000);
}
BENCHMARK(BM_Sieve_10k);

static void BM_Sieve_1M(benchmark::State& state) {
    for (auto _ : state) {
        auto result = sieve(1'000'000);
        benchmark::DoNotOptimize(result);
    }
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 1'000'000);
}
BENCHMARK(BM_Sieve_1M);

// ===========================================================================
// 2. Monte Carlo π estimation
//    Branch-heavy, FPU-bound. Shows cost of random number generation.
//    Expected ratio inside/total → π/4.
// ===========================================================================

ATTR_HOT static double monte_carlo_pi(std::uint64_t samples) {
    // Use a fixed seed for reproducibility
    std::mt19937_64 rng(42);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    std::uint64_t inside = 0;
    for (std::uint64_t i = 0; i < samples; ++i) {
        double x = dist(rng);
        double y = dist(rng);
        if (x * x + y * y <= 1.0)
            ++inside;
    }
    return 4.0 * static_cast<double>(inside) / static_cast<double>(samples);
}

static void BM_MonteCarloPi_100k(benchmark::State& state) {
    for (auto _ : state) {
        double pi = monte_carlo_pi(100'000);
        benchmark::DoNotOptimize(pi);
    }
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 100'000);
}
BENCHMARK(BM_MonteCarloPi_100k);

static void BM_MonteCarloPi_1M(benchmark::State& state) {
    for (auto _ : state) {
        double pi = monte_carlo_pi(1'000'000);
        benchmark::DoNotOptimize(pi);
    }
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 1'000'000);
}
BENCHMARK(BM_MonteCarloPi_1M);

// ===========================================================================
// 3. Matrix multiply — naïve vs cache-tiled
//    Naïve: O(N³) with poor cache locality (column-major inner loop).
//    Tiled: same complexity, but blocking improves L1/L2 hit rate.
// ===========================================================================

template <std::size_t N>
using Matrix = std::array<std::array<double, N>, N>;

template <std::size_t N>
ATTR_NOINLINE static Matrix<N> matmul_naive(const Matrix<N>& A, const Matrix<N>& B) {
    Matrix<N> C{};
    for (std::size_t i = 0; i < N; ++i)
        for (std::size_t j = 0; j < N; ++j)
            for (std::size_t k = 0; k < N; ++k)
                C[i][j] += A[i][k] * B[k][j];
    return C;
}

template <std::size_t N, std::size_t TILE = 32>
ATTR_NOINLINE static Matrix<N> matmul_tiled(const Matrix<N>& A, const Matrix<N>& B) {
    Matrix<N> C{};
    for (std::size_t ii = 0; ii < N; ii += TILE)
        for (std::size_t jj = 0; jj < N; jj += TILE)
            for (std::size_t kk = 0; kk < N; kk += TILE)
                for (std::size_t i = ii; i < std::min(ii + TILE, N); ++i)
                    for (std::size_t k = kk; k < std::min(kk + TILE, N); ++k)
                        for (std::size_t j = jj; j < std::min(jj + TILE, N); ++j)
                            C[i][j] += A[i][k] * B[k][j];
    return C;
}

static void BM_MatMul32_Naive(benchmark::State& state) {
    constexpr std::size_t N = 32;
    Matrix<N> A{}, B{};
    // Initialize with non-zero values
    for (std::size_t i = 0; i < N; ++i)
        for (std::size_t j = 0; j < N; ++j) {
            A[i][j] = static_cast<double>(i + 1);
            B[i][j] = static_cast<double>(j + 1);
        }
    for (auto _ : state) {
        auto C = matmul_naive(A, B);
        benchmark::DoNotOptimize(C);
    }
    // Report GFLOPS
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * N * N * 2 * sizeof(double));
}
BENCHMARK(BM_MatMul32_Naive);

static void BM_MatMul32_Tiled(benchmark::State& state) {
    constexpr std::size_t N = 32;
    Matrix<N> A{}, B{};
    for (std::size_t i = 0; i < N; ++i)
        for (std::size_t j = 0; j < N; ++j) {
            A[i][j] = static_cast<double>(i + 1);
            B[i][j] = static_cast<double>(j + 1);
        }
    for (auto _ : state) {
        auto C = matmul_tiled<N>(A, B);
        benchmark::DoNotOptimize(C);
    }
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * N * N * 2 * sizeof(double));
}
BENCHMARK(BM_MatMul32_Tiled);

// ===========================================================================
// 4. Newton–Raphson square root
//    FPU-bound convergence loop; shows benefit of -ffast-math / -O3 vs -O0.
// ===========================================================================

ATTR_HOT static double newton_sqrt(double x) noexcept {
    if (x <= 0.0) return 0.0;
    double guess = x * 0.5;
    // 5 iterations → < 1 ULP error for positive doubles
    for (int i = 0; i < 5; ++i)
        guess = 0.5 * (guess + x / guess);
    return guess;
}

static void BM_NewtonSqrt(benchmark::State& state) {
    const int N = static_cast<int>(state.range(0));
    std::vector<double> inputs(static_cast<std::size_t>(N));
    std::iota(inputs.begin(), inputs.end(), 1.0);

    for (auto _ : state) {
        double sum = 0.0;
        for (int i = 0; i < N; ++i)
            sum += newton_sqrt(inputs[static_cast<std::size_t>(i)]);
        benchmark::DoNotOptimize(sum);
    }
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * N);
}
BENCHMARK(BM_NewtonSqrt)->Arg(1'000)->Arg(100'000)->Arg(1'000'000);

// ===========================================================================
// 5. Recursive Fibonacci (exponential baseline)
//    Shows dramatic difference between -O0 and LTO/-O3 with memoization.
//    Intentionally NOT memoized to show worst-case recursion cost.
// ===========================================================================

ATTR_NOINLINE static std::uint64_t fib(unsigned n) noexcept {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

static void BM_FibRecursive(benchmark::State& state) {
    const auto n = static_cast<unsigned>(state.range(0));
    for (auto _ : state) {
        auto result = fib(n);
        benchmark::DoNotOptimize(result);
    }
}
// fib(35) ≈ 9.2M calls — reasonable for a benchmark, < 1 sec at -O2
BENCHMARK(BM_FibRecursive)->Arg(20)->Arg(30)->Arg(35);

// ===========================================================================
// Library-level call (kept for regression baseline)
// ===========================================================================
#include <dummy_lib/greet.h>

static void BM_Greet_Baseline(benchmark::State& state) {
    for (auto _ : state) {
        auto result = dummy_lib::greet("World");
        benchmark::DoNotOptimize(result);
        benchmark::ClobberMemory();
    }
}
BENCHMARK(BM_Greet_Baseline);

BENCHMARK_MAIN();
