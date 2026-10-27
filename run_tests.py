#!/usr/bin/env python
"""Run all backend tests and output results."""
import subprocess
import sys

result = subprocess.run(
    ["python", "-m", "pytest", "backend/tests/", "-v"],
    capture_output=True,
    text=True,
    cwd="/var/lib/alan-portfolio/workspaces/alan/api-fuzzer-alan-vo"
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
