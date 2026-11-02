"""Naive keyword filter (PRD §6 Day 4) — temporary, pre-real-defense.

Exists only to give the Mutation Engine something to evade and measure against.
Drops any chunk containing a banned literal token (case-insensitive). Crude by
design: blocking literal words is exactly the weak filter the mutation uplift
number is measured against. Toggled by DEFENSE_KEYWORD_FILTER.
"""

DEFAULT_BANNED = (
    "ignore",
    "disregard",
    "instruction",
    "system prompt",
    "api key",
    "aws_key",
)


def filter_chunks(chunks: list[str], banned: tuple[str, ...] = DEFAULT_BANNED) -> list[str]:
    low = [b.lower() for b in banned]
    return [c for c in chunks if not any(b in c.lower() for b in low)]
