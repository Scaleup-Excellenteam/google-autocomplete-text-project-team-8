#!/usr/bin/env python3
from __future__ import annotations
from functools import lru_cache
from typing import List
from pathlib import Path
import argparse
import sys

from schema import AutoCompleteData, IndexArtifacts
from indexer import build_index, save_index, load_index
from matcher import find_matches

_ARTIFACTS_PATH: str = "artifacts.pkl"


def ensure_artifacts(artifacts_path: str, index_root: str | None) -> None:
    """
    If artifacts don't exist, try to build them.
    - If index_root is provided, build from there.
    - Else try default './Archive' if exists.
    """
    p = Path(artifacts_path)
    if p.exists():
        return

    # Choose corpus root
    root = None
    if index_root:
        root = Path(index_root)
    else:
        default_root = Path("./Archive")
        if default_root.exists():
            root = default_root

    if root is None or not root.exists():
        print(
            f"[error] artifacts file '{artifacts_path}' not found and no corpus to index.\n"
            f"Run once:  python app.py --index ./Archive --artifacts {artifacts_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[info] '{artifacts_path}' not found. Building index from '{root}' ...")
    art = build_index(str(root))
    save_index(art, artifacts_path)
    print(f"[info] Indexed {art.n} sentences → {artifacts_path}")


@lru_cache(maxsize=1)
def _load_artifacts_cached(path: str) -> IndexArtifacts:
    return load_index(path)


def _artifacts() -> IndexArtifacts:
    # cache by path
    return _load_artifacts_cached(_ARTIFACTS_PATH)


def get_best_k_completions(prefix: str, k: int = 5) -> List[AutoCompleteData]:
    """
    Public API required by the spec.
    Loads artifacts lazily, finds matches, scores, sorts, and returns up to k.
    """
    if not prefix or prefix.strip() == "":
        return []

    art = _artifacts()
    matches = list(find_matches(prefix, art))

    # Sort: higher score first, then alphabetical by sentence
    matches.sort(key=lambda m: (-m.score, m.sentence_original))

    out: List[AutoCompleteData] = []
    for m in matches[:k]:
        out.append(
            AutoCompleteData(
                completed_sentence=m.sentence_original,
                source_path=m.meta["path"],
                line_no=m.meta["line_no"],
                offset=m.offset,
                score=m.score,
            )
        )
    return out


def main() -> None:
    global _ARTIFACTS_PATH

    p = argparse.ArgumentParser(description="Autocomplete POC (Phase A)")
    p.add_argument("--index", help="Path to corpus root folder (e.g., Archive/) to build index", default=None)
    p.add_argument("--artifacts", help="Path to artifacts file", default="artifacts.pkl")
    args = p.parse_args()

    _ARTIFACTS_PATH = args.artifacts

    # If explicitly asked to index now, do it and exit.
    if args.index:
        art = build_index(args.index)
        save_index(art, _ARTIFACTS_PATH)
        print(f"Indexed. Saved artifacts to {_ARTIFACTS_PATH} (n={art.n} sentences)")
        return

    # Online mode → ensure artifacts exist (auto-build if possible)
    ensure_artifacts(_ARTIFACTS_PATH, index_root=None)

    print("Autocomplete ready. Type text and press Enter. Type '#' to reset / quit.")
    while True:
        try:
            q = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if q.strip() == "#":
            print("reset / exit")
            break

        results = get_best_k_completions(q)
        if not results:
            print("(no results)")
            continue
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.completed_sentence} | {r.source_path}:{r.line_no} | offset={r.offset} | score={r.score}")


if __name__ == "__main__":
    main()
