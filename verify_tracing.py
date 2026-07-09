#!/usr/bin/env python3
"""Verification script for Phase 11: Request Tracing System."""

import sys
import subprocess
from pathlib import Path


def run_check(name, command, expected_in_output=None):
    """Run a verification check."""
    print(f"Checking: {name}...", end=" ")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"❌ FAILED")
            print(f"  Error: {result.stderr}")
            return False

        if expected_in_output and expected_in_output not in result.stdout:
            print(f"❌ FAILED")
            print(f"  Expected '{expected_in_output}' in output")
            return False

        print("✓")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def verify_files_exist():
    """Verify all expected files exist."""
    print("\n=== File Existence Checks ===")

    files = [
        "core/trace.py",
        "core/trace_integration.py",
        "core/trace_wrapper.py",
        "core/trace_viewer.py",
        "core/capability_router_traced.py",
        "core/model_client_traced.py",
        "agents/planner_traced.py",
        "friday_trace.py",
        "tests/test_trace.py",
        "tests/test_trace_integration.py",
        "demo_tracing.py",
        "TRACING.md",
        "README_TRACING.md",
        "logs/traces",
    ]

    all_exist = True
    for file in files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"❌ {file} - NOT FOUND")
            all_exist = False

    return all_exist


def verify_tests():
    """Run test suite."""
    print("\n=== Test Suite ===")

    checks = [
        ("Unit tests", "python -m pytest tests/test_trace.py -v -q"),
        ("Integration tests", "python -m pytest tests/test_trace_integration.py -v -q"),
    ]

    all_passed = True
    for name, cmd in checks:
        if not run_check(name, cmd, "passed"):
            all_passed = False

    return all_passed


def verify_cli():
    """Verify CLI commands work."""
    print("\n=== CLI Commands ===")

    checks = [
        ("friday_trace.py exists", "test -x ./friday_trace.py"),
        ("List command", "./friday_trace.py list"),
        ("Help works", "./friday_trace.py --help"),
    ]

    all_passed = True
    for name, cmd in checks:
        if not run_check(name, cmd):
            all_passed = False

    return all_passed


def verify_demo():
    """Run demonstration."""
    print("\n=== Demonstration ===")
    return run_check("Demo script", "python demo_tracing.py", "Trace saved to")


def main():
    """Run all verification checks."""
    print("=" * 80)
    print("Phase 11: Request Tracing System - Verification")
    print("=" * 80)

    results = {
        "Files": verify_files_exist(),
        "Tests": verify_tests(),
        "CLI": verify_cli(),
        "Demo": verify_demo(),
    }

    print("\n" + "=" * 80)
    print("Verification Summary")
    print("=" * 80)

    for category, passed in results.items():
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{category:20} {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All verification checks PASSED")
        print("\nPhase 11 is COMPLETE and ready to use.")
        print("\nTo enable tracing:")
        print("  export FRIDAY_TRACE=1")
        print("\nTo view traces:")
        print("  ./friday_trace.py trace")
        print("  ./friday_trace.py debug-last")
        return 0
    else:
        print("\n⚠ Some verification checks FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
