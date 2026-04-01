/**
 * bench_greet.cpp — Google Benchmark: compute-intensive math benchmarks.
 *
 * Demonstrates real performance differences between:
 *   • Sieve of Eratosthenes  (cache-friendly array access)
 *   • Monte Carlo π          (branch-heavy random simulation)
 *   • Matrix multiply        (O(N³) FLOPS, cache-hostile vs tiled)
 *   • Fibonacci (recursive)  (exponential — shows LTO/inlining gain)
 *   • Newton–Raphson √       (FPU-bound convergence loop)
 *   • Sudoku Solver          (backtracking, branch-heavy, deep call stack)
 *   • Mandelbrot Set         (FPU-bound, SIMD/vectorization-friendly)
 *   • 1D Convolution         (memory-bandwidth bound, -funroll-loops effect)
 *   • 2D Convolution         (cache-tiled vs naïve, spatial locality)
 *
 * Build variants to compare (requires -DENABLE_BENCHMARKS=ON):
 *   Debug   : cmake --preset gcc-debug-static-x86_64   -DENABLE_BENCHMARKS=ON
 *   Release : cmake --preset gcc-release-static-x86_64 -DENABLE_BENCHMARKS=ON
 *   LTO     : cmake --preset gcc-release-static-x86_64 -DENABLE_BENCHMARKS=ON -DENABLE_LTO=ON
 *
 * Run:
 *   ./build/<preset>/libs/dummy_lib/bench_greet
 *   ./build/<preset>/libs/dummy_lib/bench_greet --benchmark_filter=BM_Sudoku
 *   ./build/<preset>/libs/dummy_lib/bench_greet --benchmark_format=json \
 *       --benchmark_out=build_logs/bench_results.json
 *
 * Expected optimization ratios (Debug → Release):
 *   Sudoku     : 5–15×  (inlining, branch prediction improvement)
 *   Mandelbrot : 4–10×  (SIMD / -ffast-math)
 *   Convolution: 3–8×   (-funroll-loops, auto-vectorization)
 *   Sieve      : 2–4×   (auto-vectorization, branch elim)
 */

#include <algorithm>
#include <array>
#include <benchmark/benchmark.h>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <random>
#include <vector>

// ── compiler hints ──────────────────────────────────────────────────────────
#ifdef __GNUC__
#define ATTR_HOT      __attribute__((hot))
#define ATTR_NOINLINE __attribute__((noinline))
#else
#define ATTR_HOT
#define ATTR_NOINLINE
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
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * N * N * 2 *
                            sizeof(double));
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
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * N * N * 2 *
                            sizeof(double));
}
BENCHMARK(BM_MatMul32_Tiled);

// ===========================================================================
// 4. Newton–Raphson square root
//    FPU-bound convergence loop; shows benefit of -ffast-math / -O3 vs -O0.
// ===========================================================================

ATTR_HOT static double newton_sqrt(double x) noexcept {
    if (x <= 0.0)
        return 0.0;
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
    if (n <= 1)
        return n;
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

// ===========================================================================
// 6. Sudoku Solver (backtracking)
//    Branch-heavy, deep recursive call stack.
//    Fixed "hard" puzzle — deterministic, no RNG.
//    Measures: branch misprediction cost, inlining depth, call overhead.
//    Expected ratio Debug→Release: 5–15×
// ===========================================================================

using SudokuGrid = std::array<std::array<uint8_t, 9>, 9>;

// A known hard sudoku puzzle (0 = empty cell)
static constexpr SudokuGrid kHardPuzzle = {{
    {8, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 3, 6, 0, 0, 0, 0, 0},
    {0, 7, 0, 0, 9, 0, 2, 0, 0},
    {0, 5, 0, 0, 0, 7, 0, 0, 0},
    {0, 0, 0, 0, 4, 5, 7, 0, 0},
    {0, 0, 0, 1, 0, 0, 0, 3, 0},
    {0, 0, 1, 0, 0, 0, 0, 6, 8},
    {0, 0, 8, 5, 0, 0, 0, 1, 0},
    {0, 9, 0, 0, 0, 0, 4, 0, 0},
}};

ATTR_HOT static bool sudoku_valid(const SudokuGrid& g, int row, int col, uint8_t val) noexcept {
    // Check row and column simultaneously
    for (int i = 0; i < 9; ++i) {
        if (g[row][i] == val || g[i][col] == val)
            return false;
    }
    // Check 3×3 box
    const int br = (row / 3) * 3;
    const int bc = (col / 3) * 3;
    for (int r = br; r < br + 3; ++r)
        for (int c = bc; c < bc + 3; ++c)
            if (g[r][c] == val)
                return false;
    return true;
}

ATTR_NOINLINE static bool solve_sudoku(SudokuGrid& g) noexcept {
    for (int row = 0; row < 9; ++row) {
        for (int col = 0; col < 9; ++col) {
            if (g[row][col] != 0)
                continue;
            for (uint8_t val = 1; val <= 9; ++val) {
                if (sudoku_valid(g, row, col, val)) {
                    g[row][col] = val;
                    if (solve_sudoku(g))
                        return true;
                    g[row][col] = 0;
                }
            }
            return false; // No valid digit found
        }
    }
    return true; // All cells filled
}

static void BM_SudokuSolver(benchmark::State& state) {
    for (auto _ : state) {
        SudokuGrid g = kHardPuzzle;
        bool solved = solve_sudoku(g);
        benchmark::DoNotOptimize(solved);
        benchmark::DoNotOptimize(g);
    }
}
BENCHMARK(BM_SudokuSolver);

// ===========================================================================
// 7. Mandelbrot Set
//    FPU-bound inner loop; highly SIMD/vectorization-friendly.
//    -ffast-math allows reassociation → measurable speedup.
//    Measures: floating-point throughput, auto-vectorization width.
//    Expected ratio Debug→Release: 4–10×
// ===========================================================================

ATTR_HOT static int mandelbrot_count(double cx, double cy, int max_iter) noexcept {
    double x = 0.0, y = 0.0;
    int n = 0;
    while (x * x + y * y <= 4.0 && n < max_iter) {
        double xtemp = x * x - y * y + cx;
        y = 2.0 * x * y + cy;
        x = xtemp;
        ++n;
    }
    return n;
}

template <int W, int H>
ATTR_HOT static long mandelbrot_grid(int max_iter) noexcept {
    long total = 0;
    for (int py = 0; py < H; ++py) {
        for (int px = 0; px < W; ++px) {
            // Map pixel to complex plane: real ∈ [-2.5, 1.0], imag ∈ [-1.25, 1.25]
            double cx = -2.5 + (3.5 * px) / W;
            double cy = -1.25 + (2.5 * py) / H;
            total += mandelbrot_count(cx, cy, max_iter);
        }
    }
    return total;
}

static void BM_Mandelbrot_256(benchmark::State& state) {
    for (auto _ : state) {
        long r = mandelbrot_grid<256, 256>(128);
        benchmark::DoNotOptimize(r);
    }
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 256 * 256);
}
BENCHMARK(BM_Mandelbrot_256);

static void BM_Mandelbrot_512(benchmark::State& state) {
    for (auto _ : state) {
        long r = mandelbrot_grid<512, 512>(256);
        benchmark::DoNotOptimize(r);
    }
    state.SetItemsProcessed(static_cast<long long>(state.iterations()) * 512 * 512);
}
BENCHMARK(BM_Mandelbrot_512);

// ===========================================================================
// 8. 1D Convolution
//    Memory-bandwidth bound; benefits from -funroll-loops and SIMD.
//    Signal: N=65536 doubles. Kernel: K=64 taps.
//    Measures: memory access patterns, loop unrolling, SIMD width.
//    Expected ratio Debug→Release: 3–6×
// ===========================================================================

ATTR_HOT static void convolve_1d(const std::vector<double>& sig,
                                 const std::vector<double>& ker,
                                 std::vector<double>& out) noexcept {
    const std::size_t N = sig.size();
    const std::size_t K = ker.size();
    const std::size_t half = K / 2;
    for (std::size_t i = 0; i < N; ++i) {
        double acc = 0.0;
        const std::size_t jstart = (i >= half) ? 0 : half - i;
        const std::size_t jend = std::min(K, N + half - i);
        for (std::size_t j = jstart; j < jend; ++j)
            acc += sig[i + j - half] * ker[j];
        out[i] = acc;
    }
}

static void BM_Convolve1D(benchmark::State& state) {
    constexpr std::size_t N = 65536;
    constexpr std::size_t K = 64;
    std::vector<double> sig(N), ker(K), out(N);
    // Gaussian-like kernel (normalized)
    for (std::size_t i = 0; i < K; ++i) {
        double x = static_cast<double>(i) - K / 2.0;
        ker[i] = std::exp(-0.5 * x * x / 100.0);
    }
    std::iota(sig.begin(), sig.end(), 0.0);

    for (auto _ : state) {
        convolve_1d(sig, ker, out);
        benchmark::DoNotOptimize(out.data());
    }
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * N * K * sizeof(double));
}
BENCHMARK(BM_Convolve1D);

// ===========================================================================
// 9. 2D Convolution — naïve vs cache-tiled
//    Image: 256×256 doubles. Kernel: 7×7.
//    Cache-tiled version processes pixels in blocks to improve L1 hit rate.
//    Contrast with 1D: 2D access patterns stress both row and column strides.
//    Expected ratio (naïve→tiled at -O2): 1.5–3×; Debug→Release: 2–5×
// ===========================================================================

using Image2D = std::vector<std::vector<double>>;

ATTR_NOINLINE static void
convolve_2d_naive(const Image2D& src, const Image2D& ker, Image2D& dst) noexcept {
    const int H = static_cast<int>(src.size());
    const int W = static_cast<int>(src[0].size());
    const int KH = static_cast<int>(ker.size());
    const int KW = static_cast<int>(ker[0].size());
    const int ph = KH / 2;
    const int pw = KW / 2;
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x) {
            double acc = 0.0;
            for (int ky = 0; ky < KH; ++ky) {
                int sy = y + ky - ph;
                if (sy < 0 || sy >= H)
                    continue;
                for (int kx = 0; kx < KW; ++kx) {
                    int sx = x + kx - pw;
                    if (sx < 0 || sx >= W)
                        continue;
                    acc += src[sy][sx] * ker[ky][kx];
                }
            }
            dst[y][x] = acc;
        }
    }
}

ATTR_NOINLINE static void
convolve_2d_tiled(const Image2D& src, const Image2D& ker, Image2D& dst, int tile = 32) noexcept {
    const int H = static_cast<int>(src.size());
    const int W = static_cast<int>(src[0].size());
    const int KH = static_cast<int>(ker.size());
    const int KW = static_cast<int>(ker[0].size());
    const int ph = KH / 2;
    const int pw = KW / 2;
    for (int ty = 0; ty < H; ty += tile) {
        for (int tx = 0; tx < W; tx += tile) {
            const int yend = std::min(ty + tile, H);
            const int xend = std::min(tx + tile, W);
            for (int y = ty; y < yend; ++y) {
                for (int x = tx; x < xend; ++x) {
                    double acc = 0.0;
                    for (int ky = 0; ky < KH; ++ky) {
                        int sy = y + ky - ph;
                        if (sy < 0 || sy >= H)
                            continue;
                        for (int kx = 0; kx < KW; ++kx) {
                            int sx = x + kx - pw;
                            if (sx < 0 || sx >= W)
                                continue;
                            acc += src[sy][sx] * ker[ky][kx];
                        }
                    }
                    dst[y][x] = acc;
                }
            }
        }
    }
}

static Image2D make_image(int H, int W, double fill = 1.0) {
    return Image2D(H, std::vector<double>(W, fill));
}

static Image2D make_kernel_2d(int KH, int KW) {
    Image2D k(KH, std::vector<double>(KW));
    double sigma = 1.5;
    double sum = 0.0;
    for (int y = 0; y < KH; ++y) {
        for (int x = 0; x < KW; ++x) {
            double dy = y - KH / 2.0, dx = x - KW / 2.0;
            k[y][x] = std::exp(-(dx * dx + dy * dy) / (2.0 * sigma * sigma));
            sum += k[y][x];
        }
    }
    // Normalize
    for (auto& row : k)
        for (auto& v : row)
            v /= sum;
    return k;
}

static void BM_Convolve2D_Naive(benchmark::State& state) {
    constexpr int H = 256, W = 256, KH = 7, KW = 7;
    auto src = make_image(H, W);
    auto ker = make_kernel_2d(KH, KW);
    auto dst = make_image(H, W, 0.0);

    for (auto _ : state) {
        convolve_2d_naive(src, ker, dst);
        benchmark::DoNotOptimize(dst[0][0]);
    }
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * H * W * KH * KW *
                            sizeof(double));
}
BENCHMARK(BM_Convolve2D_Naive);

static void BM_Convolve2D_Tiled(benchmark::State& state) {
    constexpr int H = 256, W = 256, KH = 7, KW = 7;
    auto src = make_image(H, W);
    auto ker = make_kernel_2d(KH, KW);
    auto dst = make_image(H, W, 0.0);

    for (auto _ : state) {
        convolve_2d_tiled(src, ker, dst);
        benchmark::DoNotOptimize(dst[0][0]);
    }
    state.SetBytesProcessed(static_cast<long long>(state.iterations()) * H * W * KH * KW *
                            sizeof(double));
}
BENCHMARK(BM_Convolve2D_Tiled);

BENCHMARK_MAIN();
