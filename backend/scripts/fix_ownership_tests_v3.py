#!/usr/bin/env python3
"""Fix ALL remaining test failures caused by Phase 1B ownership checks.

Patterns handled:
1. Async tests: auth_headers -> auth_user, update seed helpers
2. Sync tests: expose sync_auth_user fixture, pass current_user to direct calls
3. Class-based tests: same auth_headers -> auth_user in method signatures
"""

import os
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")


def fix_file(path, fixes_description, transform_fn):
    """Apply transform_fn to file content."""
    with open(path) as f:
        original = f.read()
    result = transform_fn(original)
    if result != original:
        with open(path, "w") as f:
            f.write(result)
        print(f"  ✓ {path}: {fixes_description}")
    else:
        print(f"  - {path}: no changes needed")


# ============================================================================
# test_combat_endpoints.py
# ============================================================================


def fix_combat_endpoints(content):
    # 1. Fix _seed_session_and_character helper
    content = content.replace(
        "async def _seed_session_and_character(db_session):\n"
        '    """Create a user, character, and session for combat tests."""\n'
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    db_session.add_all([user, char, session])\n",
        "async def _seed_session_and_character(db_session, user):\n"
        '    """Create a user, character, and session for combat tests."""\n'
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    db_session.add_all([char, session])\n",
    )

    # 2-5. Process all tests: auth_headers -> auth_user, fix calls
    content = _transform_auth_headers_tests(
        content,
        seed_call="_seed_session_and_character(db_session)",
        seed_replacement="_seed_session_and_character(db_session, user)",
    )
    return content


# ============================================================================
# test_combat_actions.py
# ============================================================================


def fix_combat_actions(content):
    # 1. Fix _seed_combat helper
    content = content.replace(
        "async def _seed_combat(db_session, **overrides):\n"
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        "    sess = make_session(user=user, character=char)\n",
        "async def _seed_combat(db_session, user, **overrides):\n"
        "    char = make_character(user=user)\n"
        "    sess = make_session(user=user, character=char)\n",
    )
    content = content.replace(
        "    db_session.add_all([user, char, sess, combat])\n",
        "    db_session.add_all([char, sess, combat])\n",
    )

    # 2-5. Process all tests
    content = _transform_auth_headers_tests(
        content,
        seed_call="_seed_combat(db_session",
        seed_replacement="_seed_combat(db_session, user",
    )
    return content


# ============================================================================
# test_conversations_endpoint.py (class-based tests)
# ============================================================================


def fix_conversations_endpoint(content):
    # Fix helpers
    content = content.replace(
        "async def _create_session_in_db(db_session):\n"
        '    """Helper: create a user + character + game session and return the session."""\n'
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    db_session.add_all([user, char, session])\n"
        "    await db_session.flush()\n"
        "    return session\n",
        "async def _create_session_in_db(db_session, user):\n"
        '    """Helper: create a user + character + game session and return the session."""\n'
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    db_session.add_all([char, session])\n"
        "    await db_session.flush()\n"
        "    return session\n",
    )

    content = content.replace(
        "async def _create_full_context(db_session, *, with_quest=False, with_companion=False):\n"
        '    """Create user, character, session and optionally quest/companion.\n'
        "\n"
        "    Returns (session, character, user) tuple.\n"
        '    """\n'
        "    user = make_user()\n",
        "async def _create_full_context(db_session, user, *, with_quest=False, with_companion=False):\n"
        '    """Create user, character, session and optionally quest/companion.\n'
        "\n"
        "    Returns (session, character, user) tuple.\n"
        '    """\n',
    )
    content = content.replace(
        "    db_session.add_all([user, char, session])\n"
        "    await db_session.flush()\n"
        "\n"
        "    if with_quest:\n",
        "    db_session.add_all([char, session])\n"
        "    await db_session.flush()\n"
        "\n"
        "    if with_quest:\n",
    )

    # Transform all auth_headers usages (class methods + standalone)
    content = _transform_auth_headers_tests(
        content,
        seed_call="_create_session_in_db(db_session)",
        seed_replacement="_create_session_in_db(db_session, user)",
        extra_seeds=[
            ("_create_full_context(db_session)", "_create_full_context(db_session, user)"),
            ("_create_full_context(db_session,", "_create_full_context(db_session, user,"),
        ],
    )
    return content


# ============================================================================
# test_rest_endpoints.py (direct function calls need current_user)
# ============================================================================


def fix_rest_endpoints(content):
    # Fix sync_client to expose sync_auth_user
    content = _add_sync_auth_user_fixture(content)

    # Fix direct function calls: add current_user=user
    # take_rest calls
    content = re.sub(
        r"await take_rest\(character_id=([^,]+), request=(\w+), db=(\w+)\)",
        r"await take_rest(character_id=\1, request=\2, current_user=user, db=\3)",
        content,
    )
    # get_rest_status calls
    content = re.sub(
        r"await get_rest_status\(character_id=([^,]+), db=(\w+)\)",
        r"await get_rest_status(character_id=\1, current_user=user, db=\2)",
        content,
    )

    # Fix character-not-found direct calls that have no user
    # These functions are called with uuid.uuid4() - need a user
    # Add user creation before the "not found" tests
    content = content.replace(
        "async def test_rest_character_not_found(sync_db):\n"
        '    req = RestRequest(rest_type="short")\n'
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await take_rest(character_id=uuid.uuid4(), request=req, current_user=user, db=sync_db)\n",
        "async def test_rest_character_not_found(sync_db):\n"
        "    user = make_user()\n"
        "    sync_db.add(user)\n"
        "    sync_db.flush()\n"
        '    req = RestRequest(rest_type="short")\n'
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await take_rest(character_id=uuid.uuid4(), request=req, current_user=user, db=sync_db)\n",
    )

    content = content.replace(
        "async def test_rest_status_character_not_found(sync_db):\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await get_rest_status(character_id=uuid.uuid4(), current_user=user, db=sync_db)\n",
        "async def test_rest_status_character_not_found(sync_db):\n"
        "    user = make_user()\n"
        "    sync_db.add(user)\n"
        "    sync_db.flush()\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await get_rest_status(character_id=uuid.uuid4(), current_user=user, db=sync_db)\n",
    )

    # Fix HTTP test with int path (now UUID expected)
    content = content.replace(
        'f"{BASE}/characters/99999/rest"',
        'f"{BASE}/characters/{uuid.uuid4()}/rest"',
    )

    return content


# ============================================================================
# test_progression_endpoints.py (direct function calls need current_user)
# ============================================================================


def fix_progression_endpoints(content):
    # Fix sync_client to expose sync_auth_user
    content = _add_sync_auth_user_fixture(content)

    # Fix add_experience calls
    content = re.sub(
        r"await add_experience\(\s*character_id=([^,]+),\s*request=([^,]+),\s*db=(\w+)\s*\)",
        r"await add_experience(character_id=\1, request=\2, current_user=user, db=\3)",
        content,
    )

    # Fix get_xp_progress calls
    content = re.sub(
        r"await get_xp_progress\(character_id=([^,]+), db=(\w+)\)",
        r"await get_xp_progress(character_id=\1, current_user=user, db=\2)",
        content,
    )

    # Fix level_up_character calls
    content = re.sub(
        r"await level_up_character\(character_id=([^,]+), request=(\w+), db=(\w+)\)",
        r"await level_up_character(character_id=\1, request=\2, current_user=user, db=\3)",
        content,
    )

    # Fix not-found tests that need a user
    content = content.replace(
        "async def test_add_xp_character_not_found(sync_db):\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await add_experience(\n"
        "            character_id=uuid.uuid4(), request=AddXPRequest(amount=100), current_user=user, db=sync_db\n"
        "        )\n",
        "async def test_add_xp_character_not_found(sync_db):\n"
        "    user = make_user()\n"
        "    sync_db.add(user)\n"
        "    sync_db.flush()\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await add_experience(\n"
        "            character_id=uuid.uuid4(), request=AddXPRequest(amount=100), current_user=user, db=sync_db\n"
        "        )\n",
    )

    content = content.replace(
        "async def test_xp_progress_character_not_found(sync_db):\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await get_xp_progress(character_id=uuid.uuid4(), current_user=user, db=sync_db)\n",
        "async def test_xp_progress_character_not_found(sync_db):\n"
        "    user = make_user()\n"
        "    sync_db.add(user)\n"
        "    sync_db.flush()\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await get_xp_progress(character_id=uuid.uuid4(), current_user=user, db=sync_db)\n",
    )

    content = content.replace(
        "async def test_level_up_character_not_found(sync_db):\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await level_up_character(character_id=uuid.uuid4(), request=LevelUpRequest(), current_user=user, db=sync_db)\n",
        "async def test_level_up_character_not_found(sync_db):\n"
        "    user = make_user()\n"
        "    sync_db.add(user)\n"
        "    sync_db.flush()\n"
        "    from fastapi import HTTPException\n"
        "\n"
        "    with pytest.raises(HTTPException) as exc_info:\n"
        "        await level_up_character(character_id=uuid.uuid4(), request=LevelUpRequest(), current_user=user, db=sync_db)\n",
    )

    # Fix HTTP test with int path
    content = content.replace(
        'f"{BASE}/characters/99999/add-xp"',
        'f"{BASE}/characters/{uuid.uuid4()}/add-xp"',
    )

    return content


# ============================================================================
# test_npc_endpoints.py (sync_client, session ownership)
# ============================================================================


def fix_npc_endpoints(content):
    # Fix sync_client to expose sync_auth_user
    content = _add_sync_auth_user_fixture(content)

    # For session-based tests, need to use sync_auth_user
    # Tests that create sessions need the session's user_id to match auth_user
    # Add sync_auth_user param to tests that create sessions

    # test_add_companion
    content = content.replace(
        "async def test_add_companion(sync_client, sync_db):\n"
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        '    npc = make_character(character_type=CharacterType.NPC, name="Elara", user_id=None)\n'
        "    sync_db.add_all([user, char, session, npc])\n",
        "async def test_add_companion(sync_client, sync_db, sync_auth_user):\n"
        "    user = sync_auth_user\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        '    npc = make_character(character_type=CharacterType.NPC, name="Elara", user_id=None)\n'
        "    sync_db.add_all([char, session, npc])\n",
    )

    # test_add_companion_npc_not_found
    content = content.replace(
        "async def test_add_companion_npc_not_found(sync_client, sync_db):\n"
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    sync_db.add_all([user, char, session])\n",
        "async def test_add_companion_npc_not_found(sync_client, sync_db, sync_auth_user):\n"
        "    user = sync_auth_user\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    sync_db.add_all([char, session])\n",
    )

    # test_get_session_companions_empty
    content = content.replace(
        "async def test_get_session_companions_empty(sync_client, sync_db):\n"
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    sync_db.add_all([user, char, session])\n",
        "async def test_get_session_companions_empty(sync_client, sync_db, sync_auth_user):\n"
        "    user = sync_auth_user\n"
        "    char = make_character(user=user)\n"
        "    session = make_session(user=user, character=char)\n"
        "    sync_db.add_all([char, session])\n",
    )

    # test_get_session_companions_with_companion
    content = content.replace(
        "async def test_get_session_companions_with_companion(sync_client, sync_db):\n"
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        '    npc = make_character(character_type=CharacterType.NPC, name="Companion", user_id=None)\n'
        "    sync_db.add_all([user, char, npc])\n",
        "async def test_get_session_companions_with_companion(sync_client, sync_db, sync_auth_user):\n"
        "    user = sync_auth_user\n"
        "    char = make_character(user=user)\n"
        '    npc = make_character(character_type=CharacterType.NPC, name="Companion", user_id=None)\n'
        "    sync_db.add_all([char, npc])\n",
    )

    # test_remove_companion
    content = content.replace(
        "async def test_remove_companion(sync_client, sync_db):\n"
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        '    npc = make_character(character_type=CharacterType.NPC, name="Leaving", user_id=None)\n'
        "    sync_db.add_all([user, char, npc])\n",
        "async def test_remove_companion(sync_client, sync_db, sync_auth_user):\n"
        "    user = sync_auth_user\n"
        "    char = make_character(user=user)\n"
        '    npc = make_character(character_type=CharacterType.NPC, name="Leaving", user_id=None)\n'
        "    sync_db.add_all([char, npc])\n",
    )

    # test_remove_companion_wrong_npc
    content = content.replace(
        "async def test_remove_companion_wrong_npc(sync_client, sync_db):\n"
        "    user = make_user()\n"
        "    char = make_character(user=user)\n"
        "    npc = make_character(character_type=CharacterType.NPC, user_id=None)\n"
        "    sync_db.add_all([user, char, npc])\n",
        "async def test_remove_companion_wrong_npc(sync_client, sync_db, sync_auth_user):\n"
        "    user = sync_auth_user\n"
        "    char = make_character(user=user)\n"
        "    npc = make_character(character_type=CharacterType.NPC, user_id=None)\n"
        "    sync_db.add_all([char, npc])\n",
    )

    return content


# ============================================================================
# Shared transformation: auth_headers -> auth_user in all test functions
# ============================================================================


def _transform_auth_headers_tests(content, seed_call=None, seed_replacement=None, extra_seeds=None):
    """Transform all test functions using auth_headers to use auth_user.

    Handles both standalone functions and class methods (with self).
    """
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect test function/method signature with auth_headers
        # Patterns:
        #   async def test_xxx(..., auth_headers):
        #   async def test_xxx(..., auth_headers, ...):
        if "auth_headers" in line and ("async def test_" in line or "def test_" in line):
            # Check if this is part of a multi-line signature
            full_sig = line
            sig_start = i
            while not full_sig.rstrip().endswith(":"):
                i += 1
                if i < len(lines):
                    full_sig += "\n" + lines[i]
                else:
                    break

            if "auth_headers" in full_sig:
                # Replace auth_headers with auth_user
                full_sig = full_sig.replace("auth_headers", "auth_user")
                new_lines.append(full_sig)
                i += 1

                # Determine indentation (one level inside function body)
                # Find first non-empty body line
                body_indent = "    "
                for j in range(i, min(i + 5, len(lines))):
                    stripped = lines[j].strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith('"""'):
                        body_indent = lines[j][: len(lines[j]) - len(lines[j].lstrip())]
                        break
                    elif stripped.startswith('"""'):
                        body_indent = lines[j][: len(lines[j]) - len(lines[j].lstrip())]
                        break

                # Check if it's a class method (has self parameter)
                if "self" in full_sig:
                    body_indent = "        "  # 2 levels of indentation
                else:
                    body_indent = "    "  # 1 level

                new_lines.append(f"{body_indent}user, headers = auth_user")
                continue
            else:
                new_lines.append(full_sig)
                i += 1
                continue

        # Replace seed calls (but NOT function definitions)
        if seed_call and seed_replacement and seed_call in line and "def " not in line:
            line = line.replace(seed_call, seed_replacement)

        if extra_seeds:
            for old, new in extra_seeds:
                if old in line and "def " not in line:
                    line = line.replace(old, new)

        # Replace headers=auth_headers
        if "headers=auth_headers" in line:
            line = line.replace("headers=auth_headers", "headers=headers")

        # Replace auth_headers variable reference (standalone usage like `assert auth_headers`)
        # But NOT in function signatures (already handled above)

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


# ============================================================================
# Shared: Add sync_auth_user fixture to sync test files
# ============================================================================


def _add_sync_auth_user_fixture(content):
    """Add sync_auth_user fixture and update sync_client to use it."""
    # Check if already added
    if "sync_auth_user" in content:
        return content

    # Replace the sync_client fixture to extract auth_user
    old_sync_client = (
        "@pytest_asyncio.fixture\n"
        "async def sync_client(sync_db):\n"
        "    from app.db.models import User\n"
        "    from app.main import app\n"
        "    from app.middleware.auth import get_current_active_user\n"
        "\n"
        "    def _get_sync_db():\n"
        "        yield sync_db\n"
        "\n"
        "    auth_user = User(\n"
        "        id=uuid.uuid4(),\n"
        '        username=f"syncuser_{uuid.uuid4().hex[:8]}",\n'
        '        password_hash="hashed",\n'
        "        is_guest=False,\n"
        "        is_active=True,\n"
        "    )\n"
        "    sync_db.add(auth_user)\n"
        "    sync_db.flush()\n"
        "\n"
        "    async def _mock_auth():\n"
        "        return auth_user\n"
        "\n"
        "    app.dependency_overrides[get_db] = _get_sync_db\n"
        "    app.dependency_overrides[get_current_active_user] = _mock_auth\n"
        "    transport = ASGITransport(app=app)\n"
        '    async with AsyncClient(transport=transport, base_url="http://test") as ac:\n'
        "        yield ac\n"
        "    app.dependency_overrides.clear()"
    )

    new_sync_client = (
        "@pytest.fixture\n"
        "def sync_auth_user(sync_db):\n"
        '    """The User that sync_client authenticates as."""\n'
        "    from app.db.models import User\n"
        "\n"
        "    user = User(\n"
        "        id=uuid.uuid4(),\n"
        '        username=f"syncuser_{uuid.uuid4().hex[:8]}",\n'
        '        password_hash="hashed",\n'
        "        is_guest=False,\n"
        "        is_active=True,\n"
        "    )\n"
        "    sync_db.add(user)\n"
        "    sync_db.flush()\n"
        "    return user\n"
        "\n"
        "\n"
        "@pytest_asyncio.fixture\n"
        "async def sync_client(sync_db, sync_auth_user):\n"
        "    from app.main import app\n"
        "    from app.middleware.auth import get_current_active_user\n"
        "\n"
        "    def _get_sync_db():\n"
        "        yield sync_db\n"
        "\n"
        "    async def _mock_auth():\n"
        "        return sync_auth_user\n"
        "\n"
        "    app.dependency_overrides[get_db] = _get_sync_db\n"
        "    app.dependency_overrides[get_current_active_user] = _mock_auth\n"
        "    transport = ASGITransport(app=app)\n"
        '    async with AsyncClient(transport=transport, base_url="http://test") as ac:\n'
        "        yield ac\n"
        "    app.dependency_overrides.clear()"
    )

    content = content.replace(old_sync_client, new_sync_client)
    return content


# ============================================================================
# Main
# ============================================================================


def main():
    print("=== Phase 1B Test Ownership Fixes v3 ===\n")

    print("[1/5] Fixing test_combat_endpoints.py...")
    fix_file(
        "tests/unit/test_combat_endpoints.py",
        "seed helper + auth_headers -> auth_user",
        fix_combat_endpoints,
    )

    print("[2/5] Fixing test_combat_actions.py...")
    fix_file(
        "tests/unit/test_combat_actions.py",
        "seed helper + auth_headers -> auth_user",
        fix_combat_actions,
    )

    print("[3/5] Fixing test_rest_endpoints.py...")
    fix_file(
        "tests/unit/test_rest_endpoints.py",
        "sync_auth_user + current_user params",
        fix_rest_endpoints,
    )

    print("[4/5] Fixing test_progression_endpoints.py...")
    fix_file(
        "tests/unit/test_progression_endpoints.py",
        "sync_auth_user + current_user params",
        fix_progression_endpoints,
    )

    print("[5/5] Fixing test_npc_endpoints.py...")
    fix_file(
        "tests/unit/test_npc_endpoints.py", "sync_auth_user + session ownership", fix_npc_endpoints
    )

    print("[6/6] Fixing test_conversations_endpoint.py...")
    fix_file(
        "tests/unit/test_conversations_endpoint.py",
        "helpers + auth_headers -> auth_user",
        fix_conversations_endpoint,
    )

    # Syntax validation
    print("\n=== Syntax Validation ===")
    import py_compile

    files = [
        "tests/unit/test_combat_endpoints.py",
        "tests/unit/test_combat_actions.py",
        "tests/unit/test_rest_endpoints.py",
        "tests/unit/test_progression_endpoints.py",
        "tests/unit/test_npc_endpoints.py",
        "tests/unit/test_conversations_endpoint.py",
    ]
    all_ok = True
    for f in files:
        try:
            py_compile.compile(f, doraise=True)
            print(f"  ✓ {f}")
        except py_compile.PyCompileError as e:
            print(f"  ✗ {f}: {e}")
            all_ok = False

    if all_ok:
        print("\nAll files pass syntax validation ✓")
    else:
        print("\nSome files have syntax errors ✗")


if __name__ == "__main__":
    main()
