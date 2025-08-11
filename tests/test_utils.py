import pytest
from utils import norm

def test_norm_empty():
    # Empty string remains empty
    assert norm("") == ""

def test_norm_basic():
    # Lowercase conversion, remove punctuation, collapse spaces
    assert norm("Hello, World!") == "hello world"
    assert norm("  Spaces \t and\n newlines ") == "spaces and newlines"

def test_norm_only_punctuation():
    # Only punctuation results in empty string
    assert norm("!!!") == ""

def test_norm_mixed():
    # Word with special characters is normalized correctly
    assert norm("Test-case, with: punctuation!") == "testcase with punctuation"

def test_norm_multiple_spaces():
    # Multiple spaces collapse to a single space
    assert norm("Multiple     spaces") == "multiple spaces"
    assert norm("Tabs\tand  spaces") == "tabs and spaces"

def test_norm_numbers_and_words():
    # Numbers remain, letters become lowercase
    assert norm("Version 2.0 is out!") == "version 20 is out"

def test_norm_unicode_characters():
    # Special unicode chars (Hebrew or accents) remain, only punctuation is removed
    assert norm("שלום, עולם!") == "שלום עולם"
    assert norm("Café, crème brûlée!") == "café crème brûlée"

def test_norm_newlines_and_tabs():
    # Newlines and tabs are replaced by spaces
    assert norm("Line1\nLine2\tLine3") == "line1 line2 line3"

def test_norm_leading_trailing_spaces():
    # Leading and trailing spaces are trimmed
    assert norm("  leading and trailing  ") == "leading and trailing"

def test_norm_mixed_punctuation_and_spaces():
    # Sentence with mixed punctuation and spaces
    input_str = "Hello!!!   How's it going?   Good, I hope."
    expected = "hello hows it going good i hope"
    assert norm(input_str) == expected
