"""
Mistral v2 content extraction utility.

In v2, response content can be Union[str, List[ContentChunk]] instead of just str.
This module provides a helper to normalize content to a plain string.
"""


def extract_text_content(content) -> str:
    """Extract text from Mistral v2 content which can be str or List[ContentChunk].

    ContentChunk may be TextChunk (has .text), ImageURLChunk, ReferenceChunk, etc.
    We extract .text from items that have it, and skip non-text chunks.

    Args:
        content: str, list of ContentChunk objects, or other value

    Returns:
        Plain string with text content joined together
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for chunk in content:
            if hasattr(chunk, "text"):
                parts.append(chunk.text)
            elif isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict) and "text" in chunk:
                parts.append(chunk["text"])
        return "".join(parts)
    if content is None:
        return ""
    return str(content)
