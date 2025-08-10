#!/usr/bin/env python3
from __future__ import annotations
from functools import lru_cache
from typing import List
from pathlib import Path
import os
import shutil
import zipfile
from typing import Optional, Tuple
import argparse
import sys

from schema import AutoCompleteData, IndexArtifacts, Match
from indexer import build_index, save_index, load_index
from matcher import find_matches

_ARTIFACTS_PATH: str = "artifacts.pkl"
_DEFAULT_ARCHIVE_DIR: Path = Path("./Archive")
_DEFAULT_ARCHIVE_ZIP: Path = Path("./students_materials/Archive.zip")
_ZIP_EXTRACT_DIR: Path = Path("./.archive_extracted")


def _dir_latest_mtime(path: Path) -> float:
    """Return latest modification time among all .txt files under path; 0 if none."""
    latest = 0.0
    try:
        for p in path.rglob("*.txt"):
            try:
                m = p.stat().st_mtime
                if m > latest:
                    latest = m
            except OSError:
                continue
    except Exception:
        pass
    return latest


def _choose_corpus_source() -> Tuple[Optional[Path], str]:
    """
    Decide corpus source.
    Returns (path, kind) where kind in {"dir", "zip", "none"}.
    - Prefer './Archive' directory if it exists and has .txt files.
    - Else use 'students_materials/Archive.zip' if it exists.
    - Else (None, 'none').
    """
    if _DEFAULT_ARCHIVE_DIR.exists():
        # Ensure there is at least one .txt file
        if any(_DEFAULT_ARCHIVE_DIR.rglob("*.txt")):
            return (_DEFAULT_ARCHIVE_DIR, "dir")
    if _DEFAULT_ARCHIVE_ZIP.exists():
        return (_DEFAULT_ARCHIVE_ZIP, "zip")
    return (None, "none")


def _ensure_zip_extracted(zip_path: Path, extract_dest: Path) -> Path:
    """Extract ZIP into extract_dest (cleanly). Returns the extraction root path."""
    if extract_dest.exists():
        shutil.rmtree(extract_dest, ignore_errors=True)
    extract_dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dest)
    return extract_dest


def ensure_artifacts(artifacts_path: str, index_root: str | None) -> None:
    """
    Ensure artifacts exist and are up-to-date relative to the corpus (dir or zip).
    Behavior:
    - If user provided index_root, this function only checks freshness vs that root when needed.
    - Else it prefers './Archive' dir; else 'students_materials/Archive.zip'.
    - If artifacts are missing or stale, rebuild index automatically.
    """
    artifacts_file = Path(artifacts_path)

    # Determine corpus source
    corpus_path: Optional[Path]
    corpus_kind: str
    if index_root is not None:
        corpus_path = Path(index_root)
        corpus_kind = "dir" if corpus_path.is_dir() else ("zip" if corpus_path.suffix.lower() == ".zip" else "dir")
    else:
        corpus_path, corpus_kind = _choose_corpus_source()

    # If no corpus found
    if corpus_path is None or (corpus_kind == "dir" and not corpus_path.exists()) or (corpus_kind == "zip" and not corpus_path.exists()):
        if artifacts_file.exists():
            # We can proceed with existing artifacts even without corpus
            return
        print(
            f"[error] artifacts file '{artifacts_path}' not found and no corpus to index.\n"
            f"Extract 'students_materials/Archive.zip' or provide a corpus, or run:  python app.py --index ./Archive --artifacts {artifacts_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Compute source mtime
    if corpus_kind == "dir":
        source_mtime = _dir_latest_mtime(corpus_path)
    else:  # zip
        try:
            source_mtime = corpus_path.stat().st_mtime
        except OSError:
            source_mtime = 0.0

    # If artifacts exist and are up-to-date, nothing to do
    if artifacts_file.exists():
        try:
            artifacts_mtime = artifacts_file.stat().st_mtime
        except OSError:
            artifacts_mtime = 0.0
        if artifacts_mtime >= source_mtime > 0:
            return

    # Need to (re)build index
    if corpus_kind == "zip":
        print(f"[info] '{artifacts_path}' missing or stale. Extracting ZIP '{corpus_path}' ...")
        extracted_root = _ensure_zip_extracted(corpus_path, _ZIP_EXTRACT_DIR)
        print(f"[info] Building index from extracted corpus '{extracted_root}' ...")
        art = build_index(str(extracted_root))
    else:
        print(f"[info] '{artifacts_path}' missing or stale. Building index from '{corpus_path}' ...")
        art = build_index(str(corpus_path))
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

    p = argparse.ArgumentParser(description="Autocomplete POC (Phase A)")
    p.add_argument("--index", help="Path to corpus root folder or zip (e.g., Archive/ or Archive.zip) to build index", default=None)
    p.add_argument("--artifacts", help="Path to artifacts file", default="artifacts.pkl")
    args = p.parse_args()

    _ARTIFACTS_PATH = args.artifacts

    # If explicitly asked to index now, do it and exit.
    if args.index:
        corpus_path = Path(args.index)
        if corpus_path.suffix.lower() == ".zip":
            extracted_root = _ensure_zip_extracted(corpus_path, _ZIP_EXTRACT_DIR)
            art = build_index(str(extracted_root))
        else:
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
            display = r.completed_sentence.strip()
            print(f"{i}. {display} | {r.source_path}:{r.line_no} | offset={r.offset} | score={r.score}")


if __name__ == "__main__":
    main()
