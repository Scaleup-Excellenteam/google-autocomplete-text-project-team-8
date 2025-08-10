from __future__ import annotations
from typing import Iterable

from schema import IndexArtifacts, Match
from utils import norm
from scoring import score_match


def _find_exact_offsets(hay_norm: str, needle_norm: str) -> Iterable[int]:
    """Yield start indexes (in normalized space) for exact occurrences."""
    start = 0
    if needle_norm == "":
        return []
    while True:
        i = hay_norm.find(needle_norm, start)
        if i == -1:
            break
        yield i
        start = i + 1


def _original_offset(sentence_original: str, query_norm: str) -> int:
    """
    Heuristic mapping normalized window back to original; for POC do a casefolded literal search.
    This may be off when punctuation breaks alignment; acceptable for POC.
    """
    low = sentence_original.casefold()
    j = low.find(query_norm)
    return j if j >= 0 else 0


def find_matches(query: str, art: IndexArtifacts) -> Iterable[Match]:
    qn = norm(query)
    if not qn:
        return []

    # 1) exact substring on normalized sentences
    for sid, (s_norm, s_orig) in enumerate(zip(art.sentences_norm, art.sentences_original)):
        for _ in _find_exact_offsets(s_norm, qn):
            score = score_match(qn, "exact", None)
            off = _original_offset(s_orig, qn)
            yield Match(
                sentence_id=sid,
                sentence_original=s_orig,
                sentence_norm=s_norm,
                offset=off,
                score=score,
                meta=art.meta[sid],
            )

    # 2) TODO: single-edit matches (replace / insert / delete) with position-aware penalties
