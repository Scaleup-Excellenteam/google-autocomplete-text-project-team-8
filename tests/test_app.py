import pytest
from unittest.mock import patch, MagicMock
from app import get_best_k_completions
from schema import Match, AutoCompleteData

# Dummy artifacts mock object
class DummyArtifacts:
    n = 3
    sentences_original = ["Hello world", "Hello there", "Hi world"]
    sentences_norm = ["hello world", "hello there", "hi world"]
    meta = {
        0: {"path": "file1.txt", "line_no": 1},
        1: {"path": "file2.txt", "line_no": 2},
        2: {"path": "file3.txt", "line_no": 3},
    }

@pytest.fixture
def dummy_artifacts():
    return DummyArtifacts()

def make_match(sid, orig, norm, offset, score):
    return Match(sentence_id=sid, sentence_original=orig, sentence_norm=norm, offset=offset, score=score, meta={"path": f"file{sid}.txt", "line_no": sid+1})

# Test empty or whitespace prefix returns empty list
def test_empty_prefix_returns_empty():
    assert get_best_k_completions("") == []
    assert get_best_k_completions("    ") == []

# Test single exact match is returned correctly
@patch("app._artifacts")
@patch("app.find_matches")
def test_single_exact_match(mock_find, mock_artifacts, dummy_artifacts):
    mock_artifacts.return_value = dummy_artifacts
    # One exact match with score=10 offset=6
    mock_find.return_value = [make_match(0, "Hello world", "hello world", 6, 10)]

    results = get_best_k_completions("world")
    assert len(results) == 1
    r = results[0]
    assert r.completed_sentence == "Hello world"
    assert r.source_path == "file0.txt"
    assert r.line_no == 1
    assert r.offset == 6
    assert r.score == 10

# Test deduplication: keep best score and lowest offset
@patch("app._artifacts")
@patch("app.find_matches")
def test_deduplication_best_score_and_offset(mock_find, mock_artifacts, dummy_artifacts):
    mock_artifacts.return_value = dummy_artifacts
    # Multiple matches from same sentence_id with different scores/offsets
    mock_find.return_value = [
        make_match(0, "Hello world", "hello world", 6, 8),  # lower score
        make_match(0, "Hello world", "hello world", 4, 8),  # same score, lower offset → choose this
        make_match(0, "Hello world", "hello world", 5, 9),  # higher score → choose this one
    ]

    results = get_best_k_completions("world")
    assert len(results) == 1
    r = results[0]
    # Should pick the highest score (9), ignoring offset because score is higher
    assert r.score == 9
    assert r.offset == 5

# Test sorting by score descending and sentence alphabetically
@patch("app._artifacts")
@patch("app.find_matches")
def test_sorting_results(mock_find, mock_artifacts, dummy_artifacts):
    mock_artifacts.return_value = dummy_artifacts
    mock_find.return_value = [
        make_match(0, "banana", "banana", 0, 10),
        make_match(1, "apple", "apple", 0, 10),
        make_match(2, "cherry", "cherry", 0, 9),
    ]

    results = get_best_k_completions("a")
    # Should be sorted by score desc, then sentence alpha asc:
    # score 10: "apple", "banana" → apple before banana
    # then score 9: "cherry"
    assert len(results) == 3
    assert results[0].completed_sentence == "apple"
    assert results[1].completed_sentence == "banana"
    assert results[2].completed_sentence == "cherry"

# Test limit results to k (default k=5)
@patch("app._artifacts")
@patch("app.find_matches")
def test_limit_results_to_k(mock_find, mock_artifacts, dummy_artifacts):
    mock_artifacts.return_value = dummy_artifacts
    # Generate 10 matches with descending scores
    matches = [make_match(i, f"sentence{i}", f"sentence{i}", 0, 10 - i) for i in range(10)]
    mock_find.return_value = matches

    results = get_best_k_completions("query", k=5)
    assert len(results) == 5
    # Should be top 5 by score
    expected_sentences = [f"sentence{i}" for i in range(5)]
    actual_sentences = [r.completed_sentence for r in results]
    assert actual_sentences == expected_sentences
