from __future__ import annotations
import re

_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")

def norm(s: str) -> str:
    """Lowercase, remove punctuation, collapse whitespace (keep spaces)."""
    if not s:
        return ""
    s = _PUNCT.sub("", s).casefold()
    return _WS.sub(" ", s).strip()
