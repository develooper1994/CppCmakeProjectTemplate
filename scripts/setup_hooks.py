#!/usr/bin/env python3
import os
import sys
import stat

HOOK_CONTENT = """#!/bin/bash
# Pre-commit hook created by scripts/setup_hooks.py

echo "--> Running Pre-Commit Checks..."

# 1. Clang-Format Check
echo "    [1/3] Running Clang-Format..."
find . -name "*.cpp" -o -name "*.h" | xargs clang-format --dry-run --Werror

# 2. Clang-Tidy Check (Basic)
echo "    [2/3] Running Clang-Tidy..."
find . -name "*.cpp" | xargs clang-tidy -p build/clang-debug-static-x86_64 --quiet

# 3. Secret Scanner (Basic Regex for common keys)
echo "    [3/3] Scanning for Secrets..."
if git diff --cached | grep -Ei "API_KEY|SECRET|PASSWORD|-----BEGIN" > /dev/null; then
    echo "ERROR: Potential secret detected in your commit!"
    exit 1
fi

echo "--> Pre-Commit Checks Passed!"
exit 0
"""

def setup():
    hook_path = os.path.join('.git', 'hooks', 'pre-commit')
    
    if not os.path.exists('.git'):
        print("Error: .git directory not found. Are you at the project root?")
        sys.exit(1)

    with open(hook_path, 'w') as f:
        f.write(HOOK_CONTENT)

    # Make executable
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
    
    print("--> Git pre-commit hook installed successfully.")
    print("    Checks include: Clang-Format, Clang-Tidy, and Secret Scanning.")

if __name__ == "__main__":
    setup()
