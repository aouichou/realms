#!/usr/bin/env python3
"""
Check all model files for enum usage and verify they have create_type=False
"""

import os
import re
from pathlib import Path


def check_enum_usage():
    models_dir = Path(__file__).parent.parent / "app" / "db" / "models"
    issues = []

    for py_file in models_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        with open(py_file, "r") as f:
            content = f.read()

        # Find all Enum() calls
        enum_pattern = r"Enum\([^)]+\)"
        matches = re.finditer(enum_pattern, content, re.DOTALL)

        for match in matches:
            enum_call = match.group(0)
            line_num = content[: match.start()].count("\n") + 1

            # Check if it has create_type=False
            if "create_type=False" not in enum_call:
                issues.append(f"{py_file.name}:{line_num} - Missing create_type=False")

            # Check if it has native_enum=False
            if "native_enum=False" not in enum_call:
                issues.append(f"{py_file.name}:{line_num} - Missing native_enum=False")

    if issues:
        print("❌ Enum Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("✅ All enums have proper configuration!")
        return 0


if __name__ == "__main__":
    exit(check_enum_usage())
