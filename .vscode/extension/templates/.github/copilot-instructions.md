# Copilot Instructions

## General Project Standards
- **Modern CMake (3.25+)**: Follow target-based design.
- **Strict Isolation**: Do NOT touch `external/`. Use `SYSTEM` for vendor code.
- **Warnings**: Enable strict warnings for all internal code.
- **Testing**: Integrate with GoogleTest and CTest.
- **Documentation**: Use Doxygen and MkDocs.

## Code Conventions
- Use `PascalCase` for classes, `camelCase` for members/variables/functions/enums, and `snake_case` for files.
- Prefer `std::string_view` for constant string parameters.
- Avoid raw pointers; use smart pointers (`std::unique_ptr`, `std::shared_ptr`).
- Follow the **Arrange-Act-Assert** pattern for unit tests.
