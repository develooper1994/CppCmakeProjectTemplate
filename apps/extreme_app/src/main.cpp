#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

#include "secure_ops/secure_ops.h"

// A small deterministic, memory-safe example that computes a 64-bit
// fingerprint of a file or stdin and prints it. Avoids exceptions/RTTI
// to remain compatible with `-fno-exceptions -fno-rtti` (extreme profile).
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
    uint64_t r = secure_ops::process_input(buf.data(), buf.size());
    std::cout << std::hex << r << std::endl;
    return 0;
}
