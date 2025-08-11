from __future__ import annotations

"""
Dynamic Protobuf definitions and (de)serialization helpers for IndexArtifacts.

This avoids requiring a pre-generated artifacts_pb2.py file or protoc at build time.
Requires 'protobuf' package.
"""

from typing import Tuple

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
try:
    # Protobuf v5+ preferred API
    from google.protobuf.message_factory import GetMessageClass  # type: ignore
except Exception:  # pragma: no cover
    GetMessageClass = None  # type: ignore


_FILE_NAME = "artifacts.proto"
_PKG = "autocomplete"


def _build_file_descriptor() -> descriptor_pool.DescriptorPool:
    pool = descriptor_pool.Default()

    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = _FILE_NAME
    file_proto.package = _PKG
    file_proto.syntax = "proto3"

    # message SentenceMeta { string path = 1; uint32 line_no = 2; }
    meta_msg = file_proto.message_type.add()
    meta_msg.name = "SentenceMeta"
    f1 = meta_msg.field.add()
    f1.name = "path"
    f1.number = 1
    f1.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f1.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    f2 = meta_msg.field.add()
    f2.name = "line_no"
    f2.number = 2
    f2.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f2.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32

    # message WordStart { uint32 sentence_id = 1; uint32 pos = 2; }
    ws_msg = file_proto.message_type.add()
    ws_msg.name = "WordStart"
    w1 = ws_msg.field.add()
    w1.name = "sentence_id"
    w1.number = 1
    w1.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    w1.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    w2 = ws_msg.field.add()
    w2.name = "pos"
    w2.number = 2
    w2.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    w2.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32

    # message Posting { uint32 sentence_id = 1; uint32 pos = 2; }
    post_msg = file_proto.message_type.add()
    post_msg.name = "Posting"
    pf1 = post_msg.field.add()
    pf1.name = "sentence_id"
    pf1.number = 1
    pf1.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    pf1.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    pf2 = post_msg.field.add()
    pf2.name = "pos"
    pf2.number = 2
    pf2.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    pf2.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32

    # message TokenPostings { string token = 1; repeated Posting postings = 2; }
    tp_msg = file_proto.message_type.add()
    tp_msg.name = "TokenPostings"
    tf1 = tp_msg.field.add()
    tf1.name = "token"
    tf1.number = 1
    tf1.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    tf1.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    tf2 = tp_msg.field.add()
    tf2.name = "postings"
    tf2.number = 2
    tf2.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    tf2.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    tf2.type_name = f".{_PKG}.Posting"

    # message IndexArtifacts {
    #   repeated string sentences_original = 1;
    #   repeated string sentences_norm = 2;
    #   repeated SentenceMeta meta = 3;  // index aligned with sentences
    #   repeated WordStart word_starts = 4; // all word-start positions in normalized sentences
    #   repeated TokenPostings inv_index = 5; // inverted index for tokens → postings
    # }
    art_msg = file_proto.message_type.add()
    art_msg.name = "IndexArtifacts"
    a1 = art_msg.field.add()
    a1.name = "sentences_original"
    a1.number = 1
    a1.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    a1.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    a2 = art_msg.field.add()
    a2.name = "sentences_norm"
    a2.number = 2
    a2.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    a2.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    a3 = art_msg.field.add()
    a3.name = "meta"
    a3.number = 3
    a3.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    a3.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    a3.type_name = f".{_PKG}.SentenceMeta"
    a4 = art_msg.field.add()
    a4.name = "word_starts"
    a4.number = 4
    a4.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    a4.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    a4.type_name = f".{_PKG}.WordStart"

    a5 = art_msg.field.add()
    a5.name = "inv_index"
    a5.number = 5
    a5.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    a5.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    a5.type_name = f".{_PKG}.TokenPostings"

    # Register
    pool.Add(file_proto)
    return pool


def _get_message_classes() -> Tuple[type, type]:
    pool = _build_file_descriptor()
    meta_desc = pool.FindMessageTypeByName(f"{_PKG}.SentenceMeta")
    ws_desc = pool.FindMessageTypeByName(f"{_PKG}.WordStart")
    art_desc = pool.FindMessageTypeByName(f"{_PKG}.IndexArtifacts")
    # Prefer modern API if available
    if GetMessageClass is not None:  # type: ignore
        SentenceMeta = GetMessageClass(meta_desc)  # type: ignore
        WordStart = GetMessageClass(ws_desc)  # type: ignore
        IndexArtifactsMsg = GetMessageClass(art_desc)  # type: ignore
        return SentenceMeta, IndexArtifactsMsg
    # Fallback to legacy factory API
    factory = message_factory.MessageFactory(pool)
    SentenceMeta = factory.GetPrototype(meta_desc)  # type: ignore[attr-defined]
    WordStart = factory.GetPrototype(ws_desc)  # type: ignore[attr-defined]
    IndexArtifactsMsg = factory.GetPrototype(art_desc)  # type: ignore[attr-defined]
    return SentenceMeta, IndexArtifactsMsg


SentenceMetaMsg, IndexArtifactsMsg = _get_message_classes()


def to_protobuf_bytes(
    sentences_original: list[str],
    sentences_norm: list[str],
    meta: list[tuple[str, int]],
    word_starts: list[tuple[int, int]] | None = None,
    inv_index: dict[str, list[tuple[int, int]]] | None = None,
) -> bytes:
    msg = IndexArtifactsMsg()
    msg.sentences_original.extend(sentences_original)
    msg.sentences_norm.extend(sentences_norm)
    for path, line_no in meta:
        m = msg.meta.add()
        m.path = path
        m.line_no = int(line_no)
    if word_starts:
        for sid, pos in word_starts:
            ws = msg.word_starts.add()
            ws.sentence_id = int(sid)
            ws.pos = int(pos)
    if inv_index:
        # Write tokens in sorted order for determinism
        for tok in sorted(inv_index.keys()):
            tp = msg.inv_index.add()
            tp.token = tok
            for sid, pos in inv_index[tok]:
                p = tp.postings.add()
                p.sentence_id = int(sid)
                p.pos = int(pos)
    return msg.SerializeToString()


def from_protobuf_bytes(data: bytes) -> tuple[list[str], list[str], list[tuple[str, int]], list[tuple[int, int]], dict[str, list[tuple[int, int]]]]:
    msg = IndexArtifactsMsg()
    msg.ParseFromString(data)
    sentences_original = list(msg.sentences_original)
    sentences_norm = list(msg.sentences_norm)
    meta_list: list[tuple[str, int]] = []
    for m in msg.meta:
        meta_list.append((m.path, int(m.line_no)))
    ws_list: list[tuple[int, int]] = []
    for ws in msg.word_starts:
        ws_list.append((int(ws.sentence_id), int(ws.pos)))
    inv_index: dict[str, list[tuple[int, int]]] = {}
    try:
        for tp in msg.inv_index:
            postings: list[tuple[int, int]] = []
            for p in tp.postings:
                postings.append((int(p.sentence_id), int(p.pos)))
            inv_index[tp.token] = postings
    except Exception:
        inv_index = {}
    return sentences_original, sentences_norm, meta_list, ws_list, inv_index


