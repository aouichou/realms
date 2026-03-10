#!/usr/bin/env python3
"""Fix tests to use the authenticated user for ownership verification.

Line-by-line approach for robustness.
"""

import re
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent.parent / "tests" / "unit"

TARGET_FILES = [
    "test_adventure_endpoints.py",
    "test_combat_actions.py",
    "test_combat_endpoints.py",
    "test_conversation_endpoints.py",
    "test_conversation_endpoints_extended.py",
    "test_conversations_dm.py",
    "test_conversations_endpoint.py",
    "test_effects_endpoints.py",
    "test_endpoint_coverage.py",
    "test_inventory_endpoints.py",
    "test_memory_endpoints.py",
    "test_npc_endpoints.py",
    "test_progression_endpoints.py",
    "test_rest_endpoints.py",
    "test_session_endpoints.py",
    "test_spell_endpoints.py",
    "test_spells_casting.py",
]


def fix_file(filepath: Path) -> int:
    lines = filepath.read_text().splitlines(keepends=True)
    changes = 0

    # ------------------------------------------------------------------
    # Pass 1: Fix helper functions that create make_user() internally
    # ------------------------------------------------------------------
    i = 0
    while i < len(lines):
        # Match helper function defs
        m = re.match(
            r"^(async def (_setup_char_session|_seed|_create_test_data)\()(.+?)\)", lines[i]
        )
        if m and ", user" not in m.group(3):
            # Add user param after db_session
            old = m.group(3)
            if "db_session" in old:
                new = old.replace("db_session", "db_session, user", 1)
                lines[i] = lines[i].replace(f"({old})", f"({new})", 1)
                changes += 1

            # Remove make_user line in next few lines
            for j in range(i + 1, min(i + 10, len(lines))):
                if re.match(r"\s+user = make_user\(\)\s*$", lines[j]):
                    lines.pop(j)
                    changes += 1
                    break

            # Remove user from add_all in next few lines
            for j in range(i, min(i + 20, len(lines))):
                if j < len(lines) and "db_session.add_all" in lines[j] and "user" in lines[j]:
                    lines[j] = re.sub(r"user,\s*", "", lines[j])
                    changes += 1
                    break

        i += 1

    # ------------------------------------------------------------------
    # Pass 2: Fix test function signatures and bodies
    # ------------------------------------------------------------------
    i = 0
    while i < len(lines):
        # Detect function definition with auth_headers
        line = lines[i]

        # Single-line signature
        sig_match = re.match(r"^(\s*)(async def (test_\w+)\((.+)\):)\s*$", line)
        if sig_match and "auth_headers" in sig_match.group(4):
            indent = sig_match.group(1)
            body_indent = indent + "    "
            func_end = _find_func_end(lines, i, indent)

            # Check if body has make_user or helper
            has_make_user, has_helper = _check_body(lines, i + 1, func_end)

            if has_make_user or has_helper:
                changes += _transform_test(
                    lines,
                    i,
                    func_end,
                    indent,
                    body_indent,
                    has_make_user,
                    has_helper,
                    single_line=True,
                )
            i += 1
            continue

        # Multi-line signature start
        sig_start = re.match(r"^(\s*)(async def (test_\w+)\()", line)
        if sig_start and "auth_headers" not in line:
            i += 1
            continue
        if sig_start:
            indent = sig_start.group(1)
            body_indent = indent + "    "
            # Find the end of signature (the line with '):')
            sig_end = i
            for j in range(i, min(i + 10, len(lines))):
                if "):" in lines[j]:
                    sig_end = j
                    break

            func_end = _find_func_end(lines, sig_end, indent)
            has_make_user, has_helper = _check_body(lines, sig_end + 1, func_end)

            if has_make_user or has_helper:
                # Replace auth_headers in sig lines
                for j in range(i, sig_end + 1):
                    if "auth_headers" in lines[j]:
                        lines[j] = lines[j].replace("auth_headers", "auth_user")
                        changes += 1

                body_start = sig_end + 1
                insert_at = _skip_docstring(lines, body_start)

                # Insert user, headers = auth_user
                lines.insert(insert_at, f"{body_indent}user, headers = auth_user\n")
                changes += 1
                func_end += 1  # Adjust for insertion

                # Process body
                changes += _fix_body(lines, insert_at + 1, func_end, has_make_user, has_helper)

            i = sig_end + 1
            continue

        i += 1

    filepath.write_text("".join(lines))
    return changes


def _find_func_end(lines, sig_line, indent):
    """Find where a function body ends."""
    for j in range(sig_line + 1, len(lines)):
        stripped = lines[j]
        # Empty lines are ok
        if stripped.strip() == "":
            continue
        # Comments at any indent are ok inside function
        if stripped.strip().startswith("#"):
            # But check indent level for dedented comments
            line_indent = len(stripped) - len(stripped.lstrip())
            expected_indent = len(indent) + 4
            if line_indent < expected_indent and stripped.strip() != "":
                # Check if it's a separator comment like # ===
                if stripped.strip().startswith("# ="):
                    return j
                continue
            continue
        # Check for dedent (new function/class at same or less indent)
        line_indent = len(stripped) - len(stripped.lstrip())
        expected_indent = len(indent) + 4
        if line_indent <= len(indent) and stripped.strip() != "":
            # It's at the same indent or less - function ended
            return j
    return len(lines)


def _check_body(lines, start, end):
    """Check if function body has make_user() or helper calls."""
    has_make_user = False
    has_helper = False
    for j in range(start, min(end, len(lines))):
        if re.match(r"\s+user = make_user\(\)", lines[j]):
            has_make_user = True
        if "_setup_char_session(db_session)" in lines[j] or "_seed(db_session)" in lines[j]:
            has_helper = True
    return has_make_user, has_helper


def _skip_docstring(lines, start):
    """Skip past a docstring if present, return insertion point."""
    if start >= len(lines):
        return start
    if '"""' in lines[start]:
        if lines[start].count('"""') >= 2:
            return start + 1
        for j in range(start + 1, len(lines)):
            if '"""' in lines[j]:
                return j + 1
    return start


def _transform_test(
    lines, sig_line, func_end, indent, body_indent, has_make_user, has_helper, single_line=False
):
    """Transform a single-line signature test function."""
    changes = 0

    # Replace auth_headers -> auth_user in signature
    lines[sig_line] = lines[sig_line].replace("auth_headers", "auth_user")
    changes += 1

    body_start = sig_line + 1
    insert_at = _skip_docstring(lines, body_start)

    # Insert user, headers = auth_user
    lines.insert(insert_at, f"{body_indent}user, headers = auth_user\n")
    changes += 1
    func_end += 1  # Adjust for insertion

    changes += _fix_body(lines, insert_at + 1, func_end, has_make_user, has_helper)
    return changes


def _fix_body(lines, start, end, has_make_user, has_helper):
    """Fix the body of a test function."""
    changes = 0
    j = start
    while j < min(end, len(lines)):
        # Remove make_user line
        if has_make_user and re.match(r"\s+user = make_user\(\)\s*$", lines[j]):
            lines.pop(j)
            end -= 1
            changes += 1
            continue

        # Fix add_all removing user
        if "db_session.add_all" in lines[j] and "user," in lines[j]:
            lines[j] = re.sub(r"user,\s*", "", lines[j])
            changes += 1

        # Remove standalone db_session.add(user)
        if re.match(r"\s+db_session\.add\(user\)\s*$", lines[j]):
            lines.pop(j)
            end -= 1
            changes += 1
            continue

        # Replace auth_headers -> headers in HTTP calls
        if "headers=auth_headers" in lines[j]:
            lines[j] = lines[j].replace("headers=auth_headers", "headers=headers")
            changes += 1

        # Fix helper function calls
        if has_helper:
            if "_setup_char_session(db_session)" in lines[j]:
                lines[j] = lines[j].replace(
                    "_setup_char_session(db_session)", "_setup_char_session(db_session, user)"
                )
                changes += 1
            if "_seed(db_session)" in lines[j]:
                lines[j] = lines[j].replace("_seed(db_session)", "_seed(db_session, user)")
                changes += 1

        j += 1
    return changes


def validate_syntax(filepath: Path) -> bool:
    try:
        compile(filepath.read_text(), str(filepath), "exec")
        return True
    except SyntaxError as e:
        print(f"    SYNTAX ERROR: {e}")
        return False


def main():
    total = 0
    errors = []

    for name in TARGET_FILES:
        fp = TESTS_DIR / name
        if not fp.exists():
            print(f"  SKIP: {name}")
            continue
        n = fix_file(fp)
        ok = validate_syntax(fp)
        status = "✓" if ok else "✗"
        print(f"  {status} {name} ({n} changes)")
        total += n
        if not ok:
            errors.append(name)

    print(f"\nTotal: {total} changes")
    if errors:
        print(f"Syntax errors in: {errors}")
        sys.exit(1)
    print("All pass ✓")


if __name__ == "__main__":
    main()
