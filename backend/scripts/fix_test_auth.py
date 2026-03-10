#!/usr/bin/env python3
"""Add auth headers to test files for Phase 1A security remediation.

Processes test_session_endpoints.py, test_spell_endpoints.py, and
test_spells_casting.py to:
1. Add auth_headers or auth_user fixture to test function signatures
2. Add headers=auth_headers (or headers=headers) to all client HTTP calls
3. For session list/active tests: replace make_user() with auth_user
   and remove user_id query params
"""

import ast
import re
import sys


def add_auth_to_file(filepath, auth_user_tests=None, skip_tests=None):
    """Add auth fixtures to all async test functions in a file."""
    if auth_user_tests is None:
        auth_user_tests = set()
    if skip_tests is None:
        skip_tests = set()

    with open(filepath, "r") as f:
        lines = f.readlines()

    result = []
    current_test = None
    in_auth_user_test = False
    user_created = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect async test function definitions (including class methods)
        sig_match = re.match(r"^(\s*)async def (test_\w+)\(", line)
        if sig_match:
            indent_prefix = sig_match.group(1)
            test_name = sig_match.group(2)
            current_test = test_name

            if test_name in skip_tests:
                in_auth_user_test = False
                result.append(line)
                i += 1
                continue

            # Skip no_auth tests entirely
            if "no_auth" in test_name:
                in_auth_user_test = False
                current_test = None  # prevent HTTP call modification
                result.append(line)
                i += 1
                continue

            # Already has auth_headers — skip entirely
            if "auth_headers" in line:
                in_auth_user_test = False
                result.append(line)
                i += 1
                continue

            # Already has auth_user in signature — don't modify signature
            # but DO add headers to HTTP calls
            if "auth_user" in line:
                in_auth_user_test = True
                user_created = True  # don't try to replace make_user()
                result.append(line)
                i += 1
                continue

            if test_name in auth_user_tests:
                in_auth_user_test = True
                user_created = False
                if "(client, db_session, monkeypatch)" in line:
                    line = line.replace(
                        "(client, db_session, monkeypatch)",
                        "(client, db_session, auth_user, monkeypatch)",
                    )
                elif "(client, db_session)" in line:
                    line = line.replace("(client, db_session)", "(client, db_session, auth_user)")
                elif "(self, client, db_session)" in line:
                    line = line.replace(
                        "(self, client, db_session)", "(self, client, db_session, auth_user)"
                    )
                result.append(line)
                i += 1
                continue
            else:
                in_auth_user_test = False
                if "(client, db_session, monkeypatch)" in line:
                    line = line.replace(
                        "(client, db_session, monkeypatch)",
                        "(client, db_session, auth_headers, monkeypatch)",
                    )
                elif "(self, client, db_session, monkeypatch)" in line:
                    line = line.replace(
                        "(self, client, db_session, monkeypatch)",
                        "(self, client, db_session, auth_headers, monkeypatch)",
                    )
                elif "(self, client, db_session)" in line:
                    line = line.replace(
                        "(self, client, db_session)", "(self, client, db_session, auth_headers)"
                    )
                elif "(client, db_session)" in line:
                    line = line.replace(
                        "(client, db_session)", "(client, db_session, auth_headers)"
                    )
                elif "(self, client)" in line:
                    line = line.replace("(self, client)", "(self, client, auth_headers)")
                elif "(client)" in line:
                    line = line.replace("(client)", "(client, auth_headers)")
                result.append(line)
                i += 1
                continue

        # For auth_user tests: replace make_user() with auth_user unpacking
        if in_auth_user_test and not user_created and "    user = make_user()" in line:
            line = line.replace("user = make_user()", "user, headers = auth_user")
            user_created = True
            result.append(line)
            i += 1
            continue

        # For auth_user tests with existing auth_user: fix underscore unpacking
        if in_auth_user_test and "user, _ = auth_user" in line:
            line = line.replace("user, _ = auth_user", "user, headers = auth_user")
            result.append(line)
            i += 1
            continue

        # For auth_user tests: remove 'user' from db_session.add_all
        if in_auth_user_test and "db_session.add_all([user, " in line:
            line = line.replace("db_session.add_all([user, ", "db_session.add_all([")
            result.append(line)
            i += 1
            continue

        # Remove user_id from params for auth_user tests
        if in_auth_user_test:
            if '"user_id": str(user.id), ' in line:
                line = line.replace('"user_id": str(user.id), ', "")
            elif '"user_id": str(user.id)' in line:
                if ', params={"user_id": str(user.id)}' in line:
                    line = line.replace(', params={"user_id": str(user.id)}', "")
                elif 'params={"user_id": str(user.id)}, ' in line:
                    line = line.replace('params={"user_id": str(user.id)}, ', "")

        # Add headers to client HTTP calls
        if current_test and current_test not in skip_tests:
            has_client_call = re.search(r"await client\.(get|post|patch|delete)\(", line)
            if has_client_call and "headers=" not in line:
                headers_var = "headers" if in_auth_user_test else "auth_headers"

                stripped = line.rstrip()
                if stripped.endswith(")") or stripped.endswith("),"):
                    # Single-line call: insert headers before the last )
                    last_paren = line.rindex(")")
                    line = line[:last_paren] + f", headers={headers_var}" + line[last_paren:]
                else:
                    # Multi-line call: find closing ) via paren depth tracking
                    result.append(line)
                    i += 1
                    paren_depth = line.count("(") - line.count(")")
                    headers_already_present = False
                    while i < len(lines) and paren_depth > 0:
                        next_line = lines[i]
                        if "headers=" in next_line:
                            headers_already_present = True
                        paren_depth += next_line.count("(") - next_line.count(")")
                        if paren_depth == 0 and not headers_already_present:
                            # Ensure previous argument line has trailing comma
                            if result and not result[-1].rstrip().endswith(","):
                                result[-1] = result[-1].rstrip("\n").rstrip() + ",\n"
                            # Insert headers line before closing )
                            indent = re.match(r"^(\s*)", next_line).group(1)
                            result.append(f"{indent}    headers={headers_var},\n")
                        result.append(next_line)
                        i += 1
                    continue

        result.append(line)
        i += 1

    with open(filepath, "w") as f:
        f.writelines(result)

    # Validate syntax
    with open(filepath, "r") as f:
        source = f.read()
    try:
        ast.parse(source)
        print(f"  ✓ {filepath} — syntax OK")
    except SyntaxError as e:
        print(f"  ✗ {filepath} — SYNTAX ERROR: {e}")
        sys.exit(1)


# ============ Process test_session_endpoints.py ============
print("Processing test files...")

session_auth_user_tests = {
    "test_list_sessions",
    "test_list_sessions_active_only",
    "test_list_sessions_pagination",
    "test_get_active_session_happy",
    "test_get_active_session_not_found",
    "test_get_active_session_with_redis_state",
}

session_skip_tests = {
    "test_create_session_happy",
    "test_create_session_with_location",
    "test_create_session_with_companion",
    "test_create_session_redis_state_creation",
    "test_get_active_session_for_character_not_found",
    "test_get_active_session_for_character_happy",
}

add_auth_to_file(
    "tests/unit/test_session_endpoints.py",
    auth_user_tests=session_auth_user_tests,
    skip_tests=session_skip_tests,
)

# ============ Process test_spell_endpoints.py ============
add_auth_to_file("tests/unit/test_spell_endpoints.py")

# ============ Process test_spells_casting.py ============
add_auth_to_file("tests/unit/test_spells_casting.py")

# ============ Process remaining async test files ============
async_test_files = [
    "tests/unit/test_conversations_endpoint.py",
    "tests/unit/test_combat_endpoints.py",
    "tests/unit/test_inventory_endpoints.py",
    "tests/unit/test_endpoint_coverage.py",
    "tests/unit/test_conversations_dm.py",
    "tests/unit/test_effects_endpoints.py",
    "tests/unit/test_combat_actions.py",
    "tests/unit/test_adventure_endpoints.py",
    "tests/unit/test_conversation_endpoints_extended.py",
    "tests/unit/test_memory_endpoints.py",
    "tests/unit/test_character_endpoints.py",
    "tests/unit/test_loot_endpoints.py",
    "tests/unit/test_conversation_endpoints.py",
]

for filepath in async_test_files:
    add_auth_to_file(filepath)

print("\nAll files processed successfully!")
