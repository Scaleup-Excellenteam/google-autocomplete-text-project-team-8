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

    # message IndexArtifacts {
    #   repeated string sentences_original = 1;
    #   repeated string sentences_norm = 2;
    #   repeated SentenceMeta meta = 3;  // index aligned with sentences
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

    # Register
    pool.Add(file_proto)
    return pool


def _get_message_classes() -> Tuple[type, type]:
    pool = _build_file_descriptor()
    meta_desc = pool.FindMessageTypeByName(f"{_PKG}.SentenceMeta")
    art_desc = pool.FindMessageTypeByName(f"{_PKG}.IndexArtifacts")
    # Prefer modern API if available
    if GetMessageClass is not None:  # type: ignore
        SentenceMeta = GetMessageClass(meta_desc)  # type: ignore
        IndexArtifactsMsg = GetMessageClass(art_desc)  # type: ignore
        return SentenceMeta, IndexArtifactsMsg
    # Fallback to legacy factory API
    factory = message_factory.MessageFactory(pool)
    SentenceMeta = factory.GetPrototype(meta_desc)  # type: ignore[attr-defined]
    IndexArtifactsMsg = factory.GetPrototype(art_desc)  # type: ignore[attr-defined]
    return SentenceMeta, IndexArtifactsMsg


SentenceMetaMsg, IndexArtifactsMsg = _get_message_classes()


def to_protobuf_bytes(sentences_original: list[str], sentences_norm: list[str], meta: list[tuple[str, int]]) -> bytes:
    msg = IndexArtifactsMsg()
    msg.sentences_original.extend(sentences_original)
    msg.sentences_norm.extend(sentences_norm)
    for path, line_no in meta:
        m = msg.meta.add()
        m.path = path
        m.line_no = int(line_no)
    return msg.SerializeToString()


def from_protobuf_bytes(data: bytes) -> tuple[list[str], list[str], list[tuple[str, int]]]:
    msg = IndexArtifactsMsg()
    msg.ParseFromString(data)
    sentences_original = list(msg.sentences_original)
    sentences_norm = list(msg.sentences_norm)
    meta_list: list[tuple[str, int]] = []
    for m in msg.meta:
        meta_list.append((m.path, int(m.line_no)))
    return sentences_original, sentences_norm, meta_list


