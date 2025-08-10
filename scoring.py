from __future__ import annotations
from typing import Literal

_EditKind = Literal["exact", "sub", "ins", "del"]

# Penalty tables per spec (position is 1-based in the query)
_SUB_PENALTY = {1: 5, 2: 4, 3: 3, 4: 2}        # 5th+ → 1
_INDEL_PENALTY = {1: 10, 2: 8, 3: 6, 4: 4}     # 5th+ → 2

def _pos_penalty(pos1: int, table: dict[int, int], tail_value: int) -> int:
    if pos1 <= 0:
        return 0
    return table.get(pos1, tail_value)

def score_match(query_norm: str, edit_kind: _EditKind = "exact", edit_pos1: int | None = None) -> int:
    """
    Base = 2 * (#letters in query_norm).
    edit_pos1 is 1-based index in the query where the single edit occurred (if any).
    """
    base = 2 * len(query_norm)
    if edit_kind == "exact" or edit_pos1 is None:
        return base
    if edit_kind == "sub":
        return base - _pos_penalty(edit_pos1, _SUB_PENALTY, 1)
    # ins/del share the same table
    return base - _pos_penalty(edit_pos1, _INDEL_PENALTY, 2)
