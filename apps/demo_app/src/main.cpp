#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>

#include "dummy_lib/greet.h"

// ---------------------------------------------------------------------------
// Lightweight runtime performance metrics helper.
// Uses std::chrono high_resolution_clock for wall-time measurement and a
// simple call counter so callers can compute throughput without pulling in
// extra dependencies.
// ---------------------------------------------------------------------------

namespace perf {

/// RAII wall-clock timer.  Prints elapsed time on destruction.
class ScopedTimer {
public:
    explicit ScopedTimer(const char* label)
        : label_(label), start_(std::chrono::high_resolution_clock::now()) {}

    ~ScopedTimer() {
        auto end = std::chrono::high_resolution_clock::now();
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(end - start_).count();
        std::cout << "[perf] " << label_ << ": " << us << " µs\n";
    }

    /// Elapsed microseconds so far (non-destructive).
    [[nodiscard]] std::int64_t elapsed_us() const noexcept {
        auto now = std::chrono::high_resolution_clock::now();
        return std::chrono::duration_cast<std::chrono::microseconds>(now - start_).count();
    }

private:
    const char* label_;
    std::chrono::high_resolution_clock::time_point start_;
};

/// Simple throughput counter: records N iterations and prints ops/s.
class ThroughputCounter {
public:
    explicit ThroughputCounter(const char* label, std::int64_t iterations)
        : label_(label), iters_(iterations), start_(std::chrono::high_resolution_clock::now()) {}

    ~ThroughputCounter() {
        auto end = std::chrono::high_resolution_clock::now();
        double secs = std::chrono::duration<double>(end - start_).count();
        double ops_per_s = (secs > 0.0) ? static_cast<double>(iters_) / secs : 0.0;
        std::cout << "[perf] " << label_ << ": " << iters_ << " ops in "
                  << static_cast<std::int64_t>(secs * 1000) << " ms"
                  << "  →  " << static_cast<std::int64_t>(ops_per_s) << " ops/s\n";
    }

private:
    const char* label_;
    std::int64_t iters_;
    std::chrono::high_resolution_clock::time_point start_;
};

} // namespace perf

// ---------------------------------------------------------------------------

int main() {
    std::cout << "=== demo_app ===\n";

    // 1. Basic library call — instrumented with ScopedTimer
    {
        perf::ScopedTimer t("get_greeting()");
        std::string greeting = dummy_lib::get_greeting();
        std::cout << "Library says: " << greeting << "\n";
    }

    // 2. Throughput demo — 100 000 greeting calls
    {
        constexpr std::int64_t N = 100'000;
        perf::ThroughputCounter tc("greet loop", N);
        std::string last;
        for (std::int64_t i = 0; i < N; ++i) {
            last = dummy_lib::get_greeting();
        }
        (void)last; // prevent over-aggressive optimisation
    }

    std::cout << "=== done ===\n";
    return 0;
}
