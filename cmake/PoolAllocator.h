// cmake/PoolAllocator.h
// Lightweight std::pmr memory pool utilities for the project.
//
// Provides convenience wrappers around C++17 <memory_resource> polymorphic
// allocators.  These are *application-level* pool APIs — they do NOT replace
// the global malloc/new (that is handled by cmake/Allocators.cmake).
//
// Requirements:
//   - C++17 or later (std::pmr)
//   - No external dependencies
//
// Usage:
//   #include "PoolAllocator.h"
//
//   // Stack-backed monotonic pool (no per-dealloc overhead)
//   project::pool::StackPool<4096> pool;
//   std::pmr::vector<int> vec(pool.resource());
//
//   // Unsynchronized pool with upstream = new_delete_resource
//   project::pool::UnsyncPool heap_pool;
//   std::pmr::string str(heap_pool.resource());
//
//   // Synchronized (thread-safe) pool
//   project::pool::SyncPool safe_pool;
//   std::pmr::list<double> lst(safe_pool.resource());

#pragma once

#if __cplusplus >= 201703L

#include <array>
#include <cstddef>
#include <memory_resource>

namespace project::pool {

// -------------------------------------------------------------------------
// StackPool<N> — monotonic buffer resource backed by a stack-local buffer.
//
// Ideal for short-lived, allocation-heavy scopes (parsers, builders, etc.).
// Allocations are bump-pointer fast; memory is freed only when the pool
// is destroyed or reset().
// -------------------------------------------------------------------------
template <std::size_t N = 4096>
class StackPool {
public:
    explicit StackPool(
        std::pmr::memory_resource* upstream = std::pmr::null_memory_resource()) noexcept
        : mbr_(buf_.data(), buf_.size(), upstream) {}

    /// The polymorphic memory resource to pass to pmr containers.
    std::pmr::memory_resource* resource() noexcept { return &mbr_; }

    /// Release all memory and reset the bump pointer.
    void reset() { mbr_.release(); }

private:
    alignas(std::max_align_t) std::array<std::byte, N> buf_{};
    std::pmr::monotonic_buffer_resource mbr_;
};

// -------------------------------------------------------------------------
// UnsyncPool — unsynchronized_pool_resource with configurable upstream.
//
// Good for single-threaded workloads with mixed alloc/dealloc patterns.
// -------------------------------------------------------------------------
class UnsyncPool {
public:
    explicit UnsyncPool(
        std::pmr::memory_resource* upstream = std::pmr::new_delete_resource()) noexcept
        : pool_(std::pmr::pool_options{}, upstream) {}

    explicit UnsyncPool(
        std::pmr::pool_options opts,
        std::pmr::memory_resource* upstream = std::pmr::new_delete_resource()) noexcept
        : pool_(opts, upstream) {}

    std::pmr::memory_resource* resource() noexcept { return &pool_; }

    void release() { pool_.release(); }

private:
    std::pmr::unsynchronized_pool_resource pool_;
};

// -------------------------------------------------------------------------
// SyncPool — synchronized_pool_resource with configurable upstream.
//
// Thread-safe pool for concurrent allocation patterns.
// -------------------------------------------------------------------------
class SyncPool {
public:
    explicit SyncPool(
        std::pmr::memory_resource* upstream = std::pmr::new_delete_resource()) noexcept
        : pool_(std::pmr::pool_options{}, upstream) {}

    explicit SyncPool(
        std::pmr::pool_options opts,
        std::pmr::memory_resource* upstream = std::pmr::new_delete_resource()) noexcept
        : pool_(opts, upstream) {}

    std::pmr::memory_resource* resource() noexcept { return &pool_; }

    void release() { pool_.release(); }

private:
    std::pmr::synchronized_pool_resource pool_;
};

} // namespace project::pool

#else
#warning "PoolAllocator.h requires C++17 or later (std::pmr)"
#endif
