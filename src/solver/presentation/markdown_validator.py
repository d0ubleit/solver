"""MarkdownV2 validator for Telegram bot messages.

Usage:
    errors = validate_markdown_v2(some_text)
    if errors:
        print("MarkdownV2 parse errors:", errors)
"""

import re

# Characters reserved in Telegram MarkdownV2
_RESERVED = set(r"_*[]()~`>#+-=|{}.!")

# Patterns that are valid formatting (not errors)
_VALID_PATTERNS = [
    # Bold: *text*  (single * on each side)
    (re.compile(r'(?<!\\)\*[^*\n]+\*(?!\*)'), "*"),
    # Italic: _text_  (but not inside words)
    (re.compile(r'(?<!\\)\b_[\w\s]+_\b'), "_"),
    # Strike: ~text~
    (re.compile(r'(?<!\\)~[^~\n]+~'), "~"),
    # Spoiler: ||text||
    (re.compile(r'(?<!\\)\|\|[^|\n]+\|\|'), "|"),
    # Code: `text`
    (re.compile(r'(?<!\\)`[^`\n]+`'), "`"),
    # Links: [text](url)
    (re.compile(r'(?<!\\)\[[^\]\n]+\]\([^)\n]+\)'), "["),
]


def validate_markdown_v2(text: str) -> list[str]:
    """Validate text for Telegram MarkdownV2 compliance.

    Returns a list of error messages. Empty list = valid.
    """
    errors: list[str] = []

    # Remove valid formatting spans before checking reserved chars
    cleaned = text
    for pattern, _char in _VALID_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # Now check for unescaped reserved characters in the remaining text
    i = 0
    while i < len(cleaned):
        ch = cleaned[i]
        if ch == "\\" and i + 1 < len(cleaned):
            i += 2  # skip escaped char
            continue
        if ch in _RESERVED:
            ctx_start = max(0, i - 10)
            ctx_end = min(len(text), i + 10)
            ctx = text[ctx_start:ctx_end].replace("\n", "\\n")
            errors.append(
                f"Unescaped '{ch}' at pos {i}: ...{ctx}..."
            )
        i += 1

    return errors


def assert_valid_markdown_v2(text: str, label: str = "message") -> None:
    """Assert that text is valid MarkdownV2. Raises AssertionError with details."""
    errors = validate_markdown_v2(text)
    if errors:
        raise AssertionError(
            f"MarkdownV2 validation failed for '{label}':\n" +
            "\n".join(f"  - {e}" for e in errors) +
            f"\n\nFull text:\n{text[:500]}"
        )
