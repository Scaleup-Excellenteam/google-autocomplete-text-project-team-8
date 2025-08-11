# TODO: Add tests for fuzzy matching with one allowed edit (substitution, insertion, deletion)
# These cases are not yet implemented in the matcher, so tests for approximate matches
# should be added here once the functionality is complete.

from matcher import _find_exact_offsets, find_matches
from schema import IndexArtifacts, Match

def test_find_exact_offsets_basic():
    hay = "banana bandana"
    needle = "ana"
    offsets = list(_find_exact_offsets(hay, needle))
    # Check that all exact occurrences of 'ana' are found at the correct positions
    assert offsets == [1, 3, 11]

def test_find_matches_exact_basic():
    art = IndexArtifacts(
        n=1,
        sentences_original=["Hello World"],
        sentences_norm=["hello world"],
        meta={0: {"path": "file.txt", "line_no": 1}}
    )
    matches = list(find_matches("world", art))
    # Verify that exactly one match is found
    assert len(matches) == 1
    m = matches[0]
    # Check the match is an instance of Match class
    assert isinstance(m, Match)
    # Original sentence should be preserved correctly
    assert m.sentence_original == "Hello World"
    # Offset in the original sentence where 'world' starts
    assert m.offset == 6
    # Score should be double the length of the query for an exact match
    assert m.score == 2 * len("world")
    # Metadata should be returned properly
    assert m.meta["path"] == "file.txt"
    assert m.meta["line_no"] == 1

def test_find_matches_empty_query():
    art = IndexArtifacts(
        n=1,
        sentences_original=["Some sentence"],
        sentences_norm=["some sentence"],
        meta={0: {"path": "file.txt", "line_no": 1}}
    )
    matches = list(find_matches("", art))
    # An empty query should return an empty list of matches
    assert matches == []

