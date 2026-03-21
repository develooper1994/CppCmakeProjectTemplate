from conan import ConanFile
from conan.tools.cmake import cmake_layout


class CppCmakeProjectTemplateRecipe(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def build_requirements(self):
        # test_requires: gtest sadece test build'ine girer,
        # bu paketi kullanan downstream consumer'lara yayılmaz.
        self.test_requires("gtest/1.15.0")

    def layout(self):
        cmake_layout(self)
