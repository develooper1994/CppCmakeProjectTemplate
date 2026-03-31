#include <iostream>
#include "dummy_lib/greet.h"

int main() {
    std::cout << "Hello from demo_app!\n";
    std::cout << "Library says: " << dummy_lib::get_greeting() << "\n";
    return 0;
}
