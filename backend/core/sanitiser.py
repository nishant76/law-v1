"""
Document content sanitiser
Shared sanitisation function for all AI prompts (GAP-001).

All services must sanitise document content before injecting into LLM prompts
to prevent prompt injection attacks and ensure clean input.
"""
import re


def sanitise_document_text(raw_text: str) -> str:
    """
    Sanitise document content before injecting into AI prompt.
    GAP-001: Prevent prompt injection attacks embedded in document text.

    Strips control characters and common injection patterns.
    Does NOT alter legal text content — only removes injection attempts.

    Args:
        raw_text: Raw document text from OCR or user input

    Returns:
        Sanitised text safe for AI prompt injection
    """
    if not raw_text:
        return ""

    # Remove null bytes and non-printable control chars (keep \n \t)
    sanitised = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_text)

    # Remove common prompt injection patterns
    injection_patterns = [
        r"Assistant:\s*.*?(?=\n\n|\Z)",  # Assistant: responses
        r"SYSTEM:\s*.*?(?=\n\n|\Z)",    # SYSTEM: overrides
        r"### End of Document.*?(?=\n\n|\Z)",  # Document end markers
        r"You are now in.*?(?=\n\n|\Z)",     # Mode changes
        r"<script[^>]*>.*?</script>",        # HTML script tags
        r"<[^>]+>",                          # Other HTML tags
        r";\s*DROP\s+TABLE[^;]*;",          # SQL DROP statements
        r"'\s*OR\s*'1'\s*=\s*'1",           # SQL injection
        r";\s*SELECT\s+.*?(?=;|\Z)",        # SQL SELECT statements
    ]

    for pattern in injection_patterns:
        sanitised = re.sub(pattern, "", sanitised, flags=re.IGNORECASE | re.DOTALL)

    # Collapse runs of whitespace beyond 3 newlines (reduce token waste)
    sanitised = re.sub(r"\n{4,}", "\n\n\n", sanitised)

    # Normalise multiple spaces and tabs to single space
    sanitised = re.sub(r"[ \t]+", " ", sanitised)

    # Truncate very long inputs to prevent abuse (100KB limit)
    max_length = 100000
    if len(sanitised) > max_length:
        sanitised = sanitised[:max_length] + "...[truncated]"

    return sanitised.strip()