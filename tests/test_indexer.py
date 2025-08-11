import pytest
from pathlib import Path
from indexer import build_index

def test_build_index_single_file(tmp_path: Path):
    # Create a single .txt file with 5 lines (no empty lines)
    file = tmp_path / "file1.txt"
    file.write_text(
        "Hello world\n"
        "This is a test\n"
        "In this chapter, we begin our journey toward the CCNA\n"
        "certification by examining some networking concepts\n"
        "key to working with Cisco routers. The most important"
    )

    art = build_index(str(tmp_path))

    assert art.n == 5
    assert art.sentences_original[0] == "Hello world"
    assert art.sentences_original[1] == "This is a test"
    assert art.sentences_original[2] == "In this chapter, we begin our journey toward the CCNA"
    assert art.sentences_original[3] == "certification by examining some networking concepts"
    assert art.sentences_original[4] == "key to working with Cisco routers. The most important"

    assert art.meta[0]["line_no"] == 1
    assert art.meta[0]["path"].endswith("file1.txt")

def test_build_index_multiple_files(tmp_path: Path):
    # Create multiple .txt files with some lines each
    file1 = tmp_path / "file1.txt"
    file1.write_text("Line 1 file1\nLine 2 file1\n")
    
    file2 = tmp_path / "file2.txt"
    file2.write_text("Line 1 file2\n\nLine 3 file2\n")  # includes empty line which should be skipped
    
    file3 = tmp_path / "subdir" / "file3.txt"
    file3.parent.mkdir()
    file3.write_text("Only line in file3\n")

    art = build_index(str(tmp_path))

    # total non-empty lines = 2 + 2 + 1 = 5
    assert art.n == 5

    # Check original sentences content
    expected_sentences = [
        "Line 1 file1",
        "Line 2 file1",
        "Line 1 file2",
        "Line 3 file2",
        "Only line in file3"
    ]
    assert art.sentences_original == expected_sentences

    # Check metadata correctness
    # First file lines
    assert art.meta[0]["line_no"] == 1
    assert art.meta[1]["line_no"] == 2
    assert art.meta[0]["path"].endswith("file1.txt")
    # Second file lines
    assert art.meta[2]["line_no"] == 1
    assert art.meta[3]["line_no"] == 3
    assert art.meta[2]["path"].endswith("file2.txt")
    # Third file line
    assert art.meta[4]["line_no"] == 1
    assert art.meta[4]["path"].endswith("file3.txt")

def test_build_index_empty_lines_skipped(tmp_path: Path):
    file = tmp_path / "file.txt"
    # Some empty lines and spaces only lines
    file.write_text("\n\nLine 1\n   \nLine 2\n\n")
    
    art = build_index(str(tmp_path))
    
    assert art.n == 2
    assert art.sentences_original == ["Line 1", "Line 2"]
    assert art.meta[0]["line_no"] == 3
    assert art.meta[1]["line_no"] == 5
