import pytest
from scoring import score_match

def test_score_exact():
    # Exact match → score = 2 * len(query)
    q = "hello"
    assert score_match(q, "exact") == 2 * len(q)

def test_score_substitution_positions():
    base = 2 * 5  # "hello" length = 5
    assert score_match("hello", "sub", 1) == base - 5   # penalty table[1] = 5
    assert score_match("hello", "sub", 2) == base - 4   # penalty table[2] = 4
    assert score_match("hello", "sub", 3) == base - 3   # penalty table[3] = 3
    assert score_match("hello", "sub", 4) == base - 2   # penalty table[4] = 2
    assert score_match("hello", "sub", 5) == base - 1   # >=5 → tail penalty = 1
    assert score_match("hello", "sub", 10) == base - 1

def test_score_insertion_deletion_positions():
    base = 2 * 5
    assert score_match("hello", "ins", 1) == base - 10  # table[1] = 10
    assert score_match("hello", "del", 2) == base - 8   # table[2] = 8
    assert score_match("hello", "ins", 3) == base - 6   # table[3] = 6
    assert score_match("hello", "del", 4) == base - 4   # table[4] = 4
    assert score_match("hello", "ins", 5) == base - 2   # >=5 → tail penalty = 2
    assert score_match("hello", "del", 8) == base - 2

def test_score_position_zero_or_negative():
    base = 2 * 5
    # pos <= 0 → no penalty
    assert score_match("hello", "sub", 0) == base
    assert score_match("hello", "sub", -1) == base
    assert score_match("hello", "ins", 0) == base
    assert score_match("hello", "del", -3) == base

def test_score_none_position():
    base = 2 * 5
    # None → no penalty regardless of edit_kind
    assert score_match("hello", "sub", None) == base
    assert score_match("hello", "ins", None) == base

def test_score_treat_unknown_kind_as_indel():
    base = 2 * 5
    # Unknown edit_kind → falls into last return (treated as indel)
    assert score_match("hello", "foo", 1) == base - 10
    assert score_match("hello", "bar", 6) == base - 2

def test_score_empty_query():
    # Empty query → base = 0
    assert score_match("", "exact") == 0
    assert score_match("", "sub", 1) == -5  # penalty still applies if edit_kind != exact
    assert score_match("", "ins", 2) == -8
