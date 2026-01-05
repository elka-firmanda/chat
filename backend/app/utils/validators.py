"""
Input validation and sanitization utilities.
"""

import re
from typing import Optional

XSS_PATTERN = re.compile(r"<script[^>]*?>.*?</script>", re.IGNORECASE | re.DOTALL)

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def sanitize_input(text: str, strip_html: bool = True) -> str:
    """
    Sanitize user input to prevent XSS attacks.

    Args:
        text: The input text to sanitize
        strip_html: Whether to strip HTML tags completely (default: True)

    Returns:
        Sanitized text safe for display/storage
    """
    if not text:
        return text

    result = text

    if strip_html:
        result = HTML_TAG_PATTERN.sub("", result)
    else:
        result = XSS_PATTERN.sub("", result)
        result = re.sub(r"on\w+\s*=", "data-removed=", result, flags=re.IGNORECASE)

    result = result.strip()

    return result


def sanitize_message_content(content: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize chat message content.

    Args:
        content: The message content
        max_length: Maximum allowed length (None to skip length check)

    Returns:
        Sanitized content
    """
    if not content:
        return content

    sanitized = sanitize_input(content, strip_html=True)

    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized
