#!/usr/bin/env python3
from __future__ import annotations
from functools import lru_cache
from typing import List
from pathlib import Path
import argparse
import sys

from schema import AutoCompleteData, IndexArtifacts, Match
from proto_artifacts import from_protobuf_bytes
from matcher import find_matches
from matcher import set_word_starts
import json
import time
from datetime import datetime, timezone

_ARTIFACTS_PATH: str = "artifacts.pb"
_DEFAULT_ARTIFACTS: str = "artifacts.pb"


@lru_cache(maxsize=1)
def _load_artifacts_cached(path: str) -> IndexArtifacts:
    data = Path(path).read_bytes()
    s_orig, s_norm, meta_list, ws_list = from_protobuf_bytes(data)
    meta = {i: {"path": p, "line_no": ln} for i, (p, ln) in enumerate(meta_list)}
    if ws_list:
        # initialize matcher buckets
        set_word_starts(ws_list, s_norm)
    return IndexArtifacts(n=len(s_orig), sentences_original=s_orig, sentences_norm=s_norm, meta=meta)


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

    # Deduplicate: keep at most one suggestion per sentence_id
    # Prefer higher score, then smaller offset
    best_by_sid: dict[int, Match] = {}
    for m in matches:
        existing = best_by_sid.get(m.sentence_id)
        if existing is None:
            best_by_sid[m.sentence_id] = m
            continue
        if (m.score > existing.score) or (m.score == existing.score and m.offset < existing.offset):
            best_by_sid[m.sentence_id] = m

    deduped = list(best_by_sid.values())

    # Sort: higher score first, then alphabetical by sentence
    deduped.sort(key=lambda m: (-m.score, m.sentence_original))

    out: List[AutoCompleteData] = []
    for m in deduped[:k]:
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

    p = argparse.ArgumentParser(description="Autocomplete POC (Phase A) - Query UI")
    p.add_argument("--artifacts", help="Path to artifacts file (protobuf)", default=_DEFAULT_ARTIFACTS)
    args = p.parse_args()

    _ARTIFACTS_PATH = args.artifacts
    # Ensure artifacts exist
    if not Path(_ARTIFACTS_PATH).exists():
        print(f"[error] artifacts file '{_ARTIFACTS_PATH}' not found. Run indexing: python index_app.py --index ./Archive --out {_ARTIFACTS_PATH}", file=sys.stderr)
        sys.exit(1)

    print("Autocomplete ready. Type text and press Enter. Type '#' to reset / quit.")
    HISTORY_PATH = "history.json"
    while True:
        try:
            q = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if q.strip() == "#":
            print("reset / exit")
            break

        t0 = time.perf_counter()
        results = get_best_k_completions(q)
        t1 = time.perf_counter()
        if not results:
            print("(no results)")
            # Log minimal JSON record
            try:
                rec = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "query": q,
                    "elapsed_ms": round((t1 - t0), 2),
                    "results": [],
                }
                with open(HISTORY_PATH, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            except Exception:
                pass
            continue
        # Show only 5 sentences to user
        for i, r in enumerate(results[:5], 1):
            display = r.completed_sentence.strip()
            print(f"{i}. {display}")
        # Log full details
        try:
            rec = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "query": q,
                "elapsed_ms": round((t1 - t0), 2),
                "results": [
                    {
                        "completed_sentence": r.completed_sentence,
                        "source_path": r.source_path,
                        "line_no": r.line_no,
                        "offset": r.offset,
                        "score": r.score,
                    }
                    for r in results
                ],
            }
            with open(HISTORY_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        except Exception:
            pass
        print(f"[info] query time: {(t1 - t0):.1f} seconds")


if __name__ == "__main__":
    main()
