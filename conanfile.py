from conan import ConanFile
from conan.tools.cmake import cmake_layout


class CppCmakeProjectTemplateRecipe(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    options = {
        "allocator": ["default", "mimalloc", "jemalloc", "tcmalloc"],
    }
    default_options = {
        "allocator": "default",
    }

    def requirements(self):
        alloc = str(self.options.allocator)
        if alloc == "mimalloc":
            self.requires("mimalloc/2.1.7")
        elif alloc == "jemalloc":
            self.requires("jemalloc/5.3.0")
        elif alloc == "tcmalloc":
            self.requires("gperftools/2.15")

    def build_requirements(self):
        # test_requires: gtest is only required for test builds and
        # will not be propagated to downstream consumers.
        self.test_requires("gtest/1.15.0")

    def layout(self):
        cmake_layout(self)
