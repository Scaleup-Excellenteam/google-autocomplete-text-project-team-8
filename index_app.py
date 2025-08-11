#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
import sys
from pathlib import Path
import shutil
import zipfile
from typing import Optional, Tuple

from indexer import build_index
from proto_artifacts import to_protobuf_bytes
from utils import norm


_DEFAULT_ARCHIVE_DIR: Path = Path("./Archive")
_DEFAULT_ARCHIVE_ZIP: Path = Path("./students_materials/Archive.zip")
_ZIP_EXTRACT_DIR: Path = Path("./.archive_extracted")


def _dir_latest_mtime(path: Path) -> float:
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
    """Returns (path, kind) where kind in {"dir", "zip", "none"}."""
    if _DEFAULT_ARCHIVE_DIR.exists() and any(_DEFAULT_ARCHIVE_DIR.rglob("*.txt")):
        return (_DEFAULT_ARCHIVE_DIR, "dir")
    if _DEFAULT_ARCHIVE_ZIP.exists():
        return (_DEFAULT_ARCHIVE_ZIP, "zip")
    return (None, "none")


def _ensure_zip_extracted(zip_path: Path, extract_dest: Path) -> Path:
    if extract_dest.exists():
        shutil.rmtree(extract_dest, ignore_errors=True)
    extract_dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dest)
    return extract_dest


def _compute_word_starts(sent_norm: str) -> list[int]:
    starts: list[int] = []
    prev_space = True
    for idx, ch in enumerate(sent_norm):
        if prev_space and ch != ' ':
            starts.append(idx)
        prev_space = (ch == ' ')
    return starts


def _write_protobuf_artifacts(out_path: Path, art) -> None:
    meta_list: list[tuple[str, int]] = []
    for sid in range(art.n):
        m = art.meta[sid]
        meta_list.append((str(m["path"]), int(m["line_no"])) )
    # Precompute word starts across all sentences
    ws: list[tuple[int, int]] = []
    for sid, s_norm in enumerate(art.sentences_norm):
        for pos in _compute_word_starts(s_norm):
            ws.append((sid, pos))
    data = to_protobuf_bytes(art.sentences_original, art.sentences_norm, meta_list, word_starts=ws)
    out_path.write_bytes(data)


def ensure_artifacts(artifacts_path: str, index_root: Optional[str], force: bool = False) -> None:
    """
    Ensure artifacts exist and are up-to-date relative to the corpus (dir or zip).
    - If index_root provided, use it (dir or .zip).
    - Else prefer './Archive'; else 'students_materials/Archive.zip'.
    - If artifacts missing or stale (or force), rebuild.
    """
    artifacts_file = Path(artifacts_path)

    # Determine corpus source
    if index_root is not None:
        corpus_path = Path(index_root)
        corpus_kind = "dir" if corpus_path.is_dir() else ("zip" if corpus_path.suffix.lower() == ".zip" else "dir")
    else:
        corpus_path, corpus_kind = _choose_corpus_source()

    if corpus_path is None or not corpus_path.exists():
        if artifacts_file.exists() and not force:
            print(f"[info] No corpus found, but artifacts exist → {artifacts_file}. Skipping rebuild.")
            return
        print(
            f"[error] No corpus found. Provide --index <dir|zip> or place './Archive' or 'students_materials/Archive.zip'",
            file=sys.stderr,
        )
        sys.exit(1)

    needs_rebuild = force or (not artifacts_file.exists())
    if not needs_rebuild:
        if corpus_kind == "dir":
            source_mtime = _dir_latest_mtime(corpus_path)
        else:
            try:
                source_mtime = corpus_path.stat().st_mtime
            except OSError:
                source_mtime = 0.0
        try:
            artifacts_mtime = artifacts_file.stat().st_mtime
        except OSError:
            artifacts_mtime = 0.0
        needs_rebuild = artifacts_mtime < source_mtime

    if not needs_rebuild:
        print(f"[info] Artifacts are up-to-date → {artifacts_file}")
        return

    # Build
    if corpus_kind == "zip":
        print(f"[info] Extracting ZIP '{corpus_path}' ...")
        extracted_root = _ensure_zip_extracted(corpus_path, _ZIP_EXTRACT_DIR)
        print(f"[info] Building index from extracted corpus '{extracted_root}' ...")
        art = build_index(str(extracted_root))
    else:
        print(f"[info] Building index from '{corpus_path}' ...")
        art = build_index(str(corpus_path))

    _write_protobuf_artifacts(artifacts_file, art)
    print(f"[info] Indexed {art.n} sentences → {artifacts_file}")


def main() -> None:
    p = argparse.ArgumentParser(description="Indexing app: builds artifacts from a corpus")
    p.add_argument("--index", help="Path to corpus root folder or zip (optional)", default=None)
    p.add_argument("--out", default="artifacts.pb", help="Output artifacts file (protobuf)")
    p.add_argument("--force", action="store_true", help="Force rebuild even if artifacts appear up-to-date")
    args = p.parse_args()

    t0 = time.perf_counter()
    ensure_artifacts(args.out, index_root=args.index, force=args.force)
    t1 = time.perf_counter()
    print(f"[info] indexing wall time: {(t1 - t0):.1f} seconds")


if __name__ == "__main__":
    main()


