from __future__ import annotations
from pathlib import Path
from typing import Iterator

from schema import IndexArtifacts
from utils import norm


def _iter_sentence_lines(root: Path) -> Iterator[tuple[str, str, int]]:
    """Yield (path_str, line_stripped, line_no starting at 1) for every .txt file under root.
    A 'sentence' is a full line.
    """
    for p in root.rglob("*.txt"):
        try:
            with p.open("r", encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    s = line.rstrip("\n")
                    if s.strip() == "":
                        continue
                    yield (str(p), s, i)
        except Exception as e:
            print(f"[warn] failed reading {p}: {e}")


def build_index(root_dir: str) -> IndexArtifacts:
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"Corpus root not found: {root_dir}")

    sentences_original: list[str] = []
    sentences_norm: list[str] = []
    meta: dict[int, dict[str, int | str]] = {}

    sid = 0
    for path_str, line, line_no in _iter_sentence_lines(root):
        sentences_original.append(line)
        sentences_norm.append(norm(line))
        meta[sid] = {"path": path_str, "line_no": line_no}
        sid += 1

    return IndexArtifacts(
        n=len(sentences_original),
        sentences_original=sentences_original,
        sentences_norm=sentences_norm,
        meta=meta,
    )


# Note: Persistence is handled via protobuf in proto_artifacts.py
