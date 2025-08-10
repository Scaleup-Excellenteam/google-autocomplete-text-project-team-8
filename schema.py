from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class IndexArtifacts:
    n: int                                  # number of sentences
    sentences_original: List[str]           # sentence_id == index
    sentences_norm: List[str]               # normalized for matching
    meta: Dict[int, Dict[str, int | str]]   # sentence_id -> {"path": str, "line_no": int}

@dataclass
class Match:
    sentence_id: int
    sentence_original: str
    sentence_norm: str
    offset: int                             # start index of the match in original sentence
    score: int
    meta: Dict[str, int | str]

@dataclass
class AutoCompleteData:
    completed_sentence: str
    source_path: str
    line_no: int
    offset: int
    score: int
