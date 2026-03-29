#include <iostream>
#include "dummy_lib/greet.h"

int main() {
    std::cout << "Hello from demo_app!" << std::endl;
    std::cout << "Library says: " << dummy_lib::get_greeting() << std::endl;
    return 0;
}
