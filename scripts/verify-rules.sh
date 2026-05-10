#!/usr/bin/env bash
VIOLATIONS=0

echo "=== Checking project rules ==="

# Em dashes
if grep -r "—" src/ --include="*.py" -l 2>/dev/null | grep -q .; then
    echo "FAIL: em dash found in:"
    grep -r "—" src/ --include="*.py" -l
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "PASS: no em dashes"
fi

# AI references
if grep -ri "claude\|chatgpt\|ai-generated" src/ --include="*.py" -l 2>/dev/null | grep -q .; then
    echo "FAIL: AI reference found in:"
    grep -ri "claude\|chatgpt\|ai-generated" src/ --include="*.py" -l
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "PASS: no AI references"
fi

# Banned words
if grep -ri "straightforward\|honestly\|genuinely" src/ --include="*.py" -l 2>/dev/null | grep -q .; then
    echo "FAIL: banned word found"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "PASS: no banned words"
fi

# SPDX headers
MISSING_SPDX=0
for f in $(find src/ -name "*.py" 2>/dev/null); do
    grep -q "SPDX-License-Identifier: Apache-2.0" "$f" || {
        echo "FAIL: missing SPDX in $f"
        MISSING_SPDX=1
        VIOLATIONS=$((VIOLATIONS + 1))
    }
done
[ $MISSING_SPDX -eq 0 ] && echo "PASS: all SPDX headers present"

# Copyright headers
MISSING_CR=0
for f in $(find src/ -name "*.py" 2>/dev/null); do
    grep -q "Copyright 2026 Shivamani Vastrala" "$f" || {
        echo "FAIL: missing copyright in $f"
        MISSING_CR=1
        VIOLATIONS=$((VIOLATIONS + 1))
    }
done
[ $MISSING_CR -eq 0 ] && echo "PASS: all copyright headers present"

echo ""
echo "=== Last 5 commits ==="
git log --oneline -5

echo ""
if [ $VIOLATIONS -eq 0 ]; then
    echo "ALL CHECKS PASSED"
else
    echo "TOTAL VIOLATIONS: $VIOLATIONS -- fix before pushing"
fi
