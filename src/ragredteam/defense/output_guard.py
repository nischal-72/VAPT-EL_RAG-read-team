"""Output-side defense (PRD §6 Day 5): screen /chat responses for exfil patterns.

The primary exfil vector is a markdown image/link whose URL smuggles stolen data to
the webhook (the client fetches the image, firing the callback). This guard redacts
such patterns from the response before it is returned. Toggled by DEFENSE_OUTPUT_GUARD.
Acts within the response string only, so the frozen /chat contract is unchanged.
"""

import re

_REDACTION = "[blocked: possible exfiltration link]"

_PATTERNS = (
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),                      # markdown image
    re.compile(r"\[[^\]]*\]\((?:https?|data):[^)]*\)", re.I),  # markdown link
    re.compile(r"(?:https?://|www\.)\S*?/collect\S*", re.I),   # bare webhook URL
)


def screen(response: str) -> tuple[str, bool]:
    """Return (possibly-redacted response, whether anything was blocked)."""
    blocked = False
    out = response
    for pattern in _PATTERNS:
        out, n = pattern.subn(_REDACTION, out)
        blocked = blocked or n > 0
    return out, blocked
