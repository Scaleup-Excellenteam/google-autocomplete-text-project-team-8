import tempfile
from pathlib import Path
import shutil
import os
import pytest

from index_app import ensure_artifacts

def create_sample_txt_files(tmp_dir: Path):
    """Create sample .txt files with content for testing."""
    folder = tmp_dir / "sample_corpus"
    folder.mkdir()
    file1 = folder / "file1.txt"
    file2 = folder / "file2.txt"
    file1.write_text("Hello world\nThis is a test\n")
    file2.write_text("Another line\nMore text\n")
    return folder

def test_ensure_artifacts_creates_files(tmp_path):
    """
    Test that ensure_artifacts creates the artifact file
    when given a valid directory containing .txt files.
    """
    corpus_dir = create_sample_txt_files(tmp_path)
    artifacts_path = tmp_path / "artifacts.pb"
    # Call ensure_artifacts with the corpus directory
    ensure_artifacts(str(artifacts_path), str(corpus_dir), force=True)
    # Check that the artifacts file was created
    assert artifacts_path.exists()
    # File size should be > 0
    assert artifacts_path.stat().st_size > 0

def test_ensure_artifacts_contents(tmp_path):
    """
    Test that the content of the artifact file is not empty
    and that ensure_artifacts does not overwrite
    if the artifacts are up to date (force=False).
    """
    corpus_dir = create_sample_txt_files(tmp_path)
    artifacts_path = tmp_path / "artifacts.pb"

    # First call with force=True to create artifacts
    ensure_artifacts(str(artifacts_path), str(corpus_dir), force=True)
    size_first = artifacts_path.stat().st_size

    # Call again without force, should skip rebuild
    ensure_artifacts(str(artifacts_path), str(corpus_dir), force=False)
    size_second = artifacts_path.stat().st_size

    assert size_first == size_second

    # Clean up
    shutil.rmtree(corpus_dir)
