#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

#include "secure_ops/secure_ops.h"

#ifdef FUZZ_LIBFUZZER
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    // Keep result volatile to avoid optimization away in fuzz builds
    volatile uint64_t r = secure_ops::process_input(data, size);
    (void)r;
    return 0;
}
#else
int main(int argc, char** argv) {
    std::vector<uint8_t> buf;
    if (argc > 1) {
        std::ifstream f(argv[1], std::ios::binary);
        buf.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    } else {
        std::istreambuf_iterator<char> it(std::cin);
        std::istreambuf_iterator<char> end;
        while (it != end) {
            buf.push_back(static_cast<uint8_t>(*it));
            ++it;
        }
    }
    volatile uint64_t r = secure_ops::process_input(buf.data(), buf.size());
    (void)r;
    return 0;
}
#endif
