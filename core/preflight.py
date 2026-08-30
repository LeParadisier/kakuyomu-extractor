"""Environment and dependency verification module."""

import importlib.util
import sys
from pathlib import Path


def check_module(module_name: str) -> bool:
    """Check if a Python module is installed."""
    return importlib.util.find_spec(module_name) is not None


def run_preflight_check(enable_ai: bool) -> bool:
    """Perform environment checks for core extraction and optional AI dependencies."""
    print("\n=== PRE-FLIGHT CHECK ===")

    # Python Version
    py_ver = sys.version_info
    print(f"[OK] Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")

    # Core dependencies
    core_deps = ["requests", "bs4", "lxml"]
    missing_core = [dep for dep in core_deps if not check_module(dep)]

    for dep in core_deps:
        if dep not in missing_core:
            print(f"[OK] {dep}")
        else:
            print(f"[FAIL] {dep} is missing.")

    if missing_core:
        print("\n[ERROR] Missing core dependencies. Install them via:")
        print(f"pip install {' '.join(missing_core)}")
        return False

    # AI dependencies
    if enable_ai:
        ai_deps = {"google.genai": "google-genai", "yaml": "PyYAML"}
        missing_ai = []

        for mod, pkg in ai_deps.items():
            if check_module(mod):
                print(f"[OK] {pkg}")
            else:
                print(f"[FAIL] {pkg} is missing.")
                missing_ai.append(pkg)

        if missing_ai:
            print("\n[ERROR] Missing AI dependencies. Install them via:")
            print(f"pip install {' '.join(missing_ai)}")
            return False
    else:
        print("AI translation: disabled")

    return True