#!/usr/bin/env python3
"""
Simple test runner - just check if all tests pass or fail
"""

import subprocess
import sys
import os

def run_tests():
    print("🧪 Running All Tests...")
    print("=" * 50)

    # Change to app directory so imports work correctly
    if os.path.exists("/app"):
        os.chdir("/app")

    # Find all test files
    test_files = [
        "tests/test_behavioral_e2e.py",
        "tests/test_validation_e2e.py",
        "tests/test_natural_vs_observed.py"
    ]

    # Check which files exist
    existing_files = []
    for test_file in test_files:
        if os.path.exists(test_file):
            existing_files.append(test_file)
        else:
            print(f"⚠️  {test_file} not found, skipping...")

    if not existing_files:
        print("❌ No test files found!")
        return False

    # Run pytest on all existing test files
    cmd = [
        "python", "-m", "pytest",
        "--asyncio-mode=auto",
        "-v"
    ] + existing_files

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Print the output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check if all tests passed
        if result.returncode == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return True
        else:
            print(f"\n❌ TESTS FAILED (exit code: {result.returncode})")
            return False

    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)