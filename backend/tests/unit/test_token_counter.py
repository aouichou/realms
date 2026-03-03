"""Tests for app.services.token_counter.TokenCounter."""

from app.services.token_counter import TokenCounter

# ── count_tokens ───────────────────────────────────────────────────────────


def test_count_tokens_empty():
    assert TokenCounter.count_tokens("") == 0


def test_count_tokens_short_text():
    # "Hi" is 2 chars → 2 // 4 = 0
    assert TokenCounter.count_tokens("Hi") == 0
    # "Hello!" is 6 chars → 6 // 4 = 1
    assert TokenCounter.count_tokens("Hello!") == 1


def test_count_tokens_exact_multiple():
    text = "a" * 20  # 20 chars → 20 // 4 = 5
    assert TokenCounter.count_tokens(text) == 5


# ── count_message_tokens ──────────────────────────────────────────────────


def test_count_message_tokens_single_message():
    msgs = [{"role": "user", "content": "a" * 16}]  # 16 // 4 = 4 tokens + 4 overhead = 8
    assert TokenCounter.count_message_tokens(msgs) == 8


def test_count_message_tokens_multiple():
    msgs = [
        {"role": "system", "content": "a" * 8},  # 2 + 4 = 6
        {"role": "user", "content": "a" * 12},  # 3 + 4 = 7
    ]
    assert TokenCounter.count_message_tokens(msgs) == 13


# ── fits_in_context ───────────────────────────────────────────────────────


def test_fits_in_context_true():
    msgs = [{"role": "user", "content": "short"}]
    assert TokenCounter.fits_in_context(msgs, max_tokens=100) is True


def test_fits_in_context_false():
    # One message with 400 chars → 100 tokens + 4 overhead = 104
    msgs = [{"role": "user", "content": "a" * 400}]
    assert TokenCounter.fits_in_context(msgs, max_tokens=50) is False


# ── truncate_to_fit ──────────────────────────────────────────────────────


def test_truncate_below_limit_returns_same():
    msgs = [{"role": "user", "content": "tiny"}]
    result = TokenCounter.truncate_to_fit(msgs, max_tokens=1000)
    assert result == msgs


def test_truncate_preserves_system_messages():
    system_msg = {"role": "system", "content": "system prompt " * 5}
    old_msg = {"role": "user", "content": "a" * 400}
    recent_msg = {"role": "assistant", "content": "short reply"}
    msgs = [system_msg, old_msg, recent_msg]

    result = TokenCounter.truncate_to_fit(msgs, max_tokens=50)

    # System messages must always be preserved
    roles = [m["role"] for m in result]
    assert "system" in roles


def test_truncate_drops_older_conversation_messages():
    system_msg = {"role": "system", "content": "sys"}
    old_msg = {"role": "user", "content": "x" * 200}
    mid_msg = {"role": "assistant", "content": "y" * 200}
    recent_msg = {"role": "user", "content": "z" * 4}
    msgs = [system_msg, old_msg, mid_msg, recent_msg]

    result = TokenCounter.truncate_to_fit(msgs, max_tokens=30)

    # The recent message should be present, older ones may be dropped
    contents = [m["content"] for m in result]
    assert system_msg["content"] in contents
    assert recent_msg["content"] in contents


def test_truncate_keeps_recent_messages():
    system_msg = {"role": "system", "content": "s"}
    msgs = [system_msg] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i} " * 5}
        for i in range(20)
    ]
    result = TokenCounter.truncate_to_fit(msgs, max_tokens=60)

    # System message always kept
    assert result[0]["role"] == "system"
    # The most recent conversation message should be kept
    assert result[-1]["content"] == msgs[-1]["content"]
