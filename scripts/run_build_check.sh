#!/usr/bin/env bash
# run_build_check.sh — Configure + Build + Test, tüm çıktıyı loglar

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/build_logs"
PRESET="gcc-debug-static-x86_64"

mkdir -p "$LOG_DIR"

echo "========================================"
echo " CppCmakeProjectTemplate Build Check"
echo " Preset : $PRESET"
echo " Root   : $PROJECT_ROOT"
echo "========================================"

cd "$PROJECT_ROOT"

# 1. Temizle
echo ""
echo "[1/3] CMake Configure..."
cmake --preset "$PRESET" 2>&1 | tee "$LOG_DIR/configure.log"
CONFIGURE_EXIT=${PIPESTATUS[0]}

if [ $CONFIGURE_EXIT -ne 0 ]; then
    echo ""
    echo "❌ Configure FAILED (exit $CONFIGURE_EXIT)"
    echo "   Log: $LOG_DIR/configure.log"
    exit 1
fi
echo "✅ Configure OK"

# 2. Build
echo ""
echo "[2/3] CMake Build..."
cmake --build --preset "$PRESET" 2>&1 | tee "$LOG_DIR/build.log"
BUILD_EXIT=${PIPESTATUS[0]}

if [ $BUILD_EXIT -ne 0 ]; then
    echo ""
    echo "❌ Build FAILED (exit $BUILD_EXIT)"
    echo "   Log: $LOG_DIR/build.log"
    exit 1
fi
echo "✅ Build OK"

# 3. Test
echo ""
echo "[3/3] CTest..."
ctest --preset "$PRESET" --output-on-failure 2>&1 | tee "$LOG_DIR/test.log"
TEST_EXIT=${PIPESTATUS[0]}

if [ $TEST_EXIT -ne 0 ]; then
    echo ""
    echo "❌ Tests FAILED (exit $TEST_EXIT)"
    echo "   Log: $LOG_DIR/test.log"
    exit 1
fi
echo "✅ Tests OK"

echo ""
echo "[4/4] Extension template sync..."
python3 "$PROJECT_ROOT/scripts/sync_to_extension.py" --apply 2>&1 | tee "$LOG_DIR/sync.log"
echo "✅ Sync OK"

echo ""
echo "========================================"
echo "✅ Tüm adımlar başarılı!"
echo "   Loglar: $LOG_DIR/"
echo "========================================"
