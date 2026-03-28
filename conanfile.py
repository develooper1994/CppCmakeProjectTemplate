from conan import ConanFile
from conan.tools.cmake import cmake_layout


class CppCmakeProjectTemplateRecipe(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def build_requirements(self):
        # test_requires: gtest is only required for test builds and
        # will not be propagated to downstream consumers.
        self.test_requires("gtest/1.15.0")

    def layout(self):
        cmake_layout(self)
