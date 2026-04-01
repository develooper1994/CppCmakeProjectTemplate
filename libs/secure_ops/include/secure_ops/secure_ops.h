// secure_ops: small, safe processing helpers intended for fuzzing and hardening
#pragma once

#include <cstddef>
#include <cstdint>

namespace secure_ops {

// Process input bytes in a deterministic, safe way and return a 64-bit value.
// Must be noexcept and avoid exceptions/RTTI for extreme hardening builds.
uint64_t process_input(const uint8_t* data, size_t size) noexcept;

} // namespace secure_ops
