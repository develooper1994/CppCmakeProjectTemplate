# GUI Application

Qt-based GUI application for the C++ CMake Project Template.

## Requirements

- Qt 5 or Qt 6 (Widgets + optional QML)
- Enable via: `-DENABLE_QT=ON` (and `-DENABLE_QML=ON` for QML support)

## Build

```bash
cmake --preset gcc-debug-static-x86_64 -DENABLE_QT=ON
cmake --build --preset gcc-debug-static-x86_64
```
