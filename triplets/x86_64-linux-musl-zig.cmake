# vcpkg custom triplet: x86_64 Linux musl via Zig cc (fully static)
#
# Usage:
#   vcpkg install --overlay-triplets=triplets [packages]
#   cmake -DVCPKG_OVERLAY_TRIPLETS=triplets ...

set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE static)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_CMAKE_SYSTEM_NAME Linux)
set(VCPKG_CHAINLOAD_TOOLCHAIN_FILE "${CMAKE_CURRENT_LIST_DIR}/../cmake/toolchains/x86_64-linux-musl-zig.cmake")
