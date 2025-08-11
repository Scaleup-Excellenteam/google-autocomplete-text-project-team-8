import pytest
from proto_artifacts import to_protobuf_bytes, from_protobuf_bytes

def test_protobuf_roundtrip():
    sentences_original = ["Hello world", "Test sentence"]
    sentences_norm = ["hello world", "test sentence"]
    meta = [("file1.txt", 1), ("file2.txt", 2)]

    data = to_protobuf_bytes(sentences_original, sentences_norm, meta)
    assert isinstance(data, bytes)

    so2, sn2, meta2 = from_protobuf_bytes(data)
    assert so2 == sentences_original
    assert sn2 == sentences_norm
    assert meta2 == meta

def test_protobuf_empty_lists():
    data = to_protobuf_bytes([], [], [])
    so, sn, m = from_protobuf_bytes(data)
    assert so == []
    assert sn == []
    assert m == []

def test_protobuf_meta_types():
    sentences_original = ["Example"]
    sentences_norm = ["example"]
    meta = [("path/to/file.txt", 42)]

    data = to_protobuf_bytes(sentences_original, sentences_norm, meta)
    _, _, meta2 = from_protobuf_bytes(data)
    assert isinstance(meta2[0][0], str)
    assert isinstance(meta2[0][1], int)
    assert meta2[0][1] == 42
