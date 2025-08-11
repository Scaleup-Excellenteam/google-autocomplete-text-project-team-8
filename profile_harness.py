from __future__ import annotations

import argparse
import time
from pathlib import Path

from indexer import build_index
from proto_artifacts import to_protobuf_bytes, from_protobuf_bytes
from app import get_best_k_completions


def profile_index(index_path: str, artifacts_path: str) -> None:
    t0 = time.perf_counter()
    art = build_index(index_path)
    meta_list: list[tuple[str, int]] = []
    for sid in range(art.n):
        m = art.meta[sid]
        meta_list.append((str(m["path"]), int(m["line_no"])) )
    data = to_protobuf_bytes(art.sentences_original, art.sentences_norm, meta_list)
    Path(artifacts_path).write_bytes(data)
    t1 = time.perf_counter()
    print(f"index_time_sec={t1 - t0:.3f} n_sentences={art.n}")


def profile_queries(queries_file: str, k: int = 5) -> None:
    queries = [q.strip() for q in Path(queries_file).read_text(encoding="utf-8").splitlines() if q.strip()]
    t0 = time.perf_counter()
    total = 0
    for q in queries:
        res = get_best_k_completions(q, k=k)
        total += len(res)
    t1 = time.perf_counter()
    print(f"queries={len(queries)} total_results={total} elapsed_sec={t1 - t0:.3f} qps={len(queries)/(t1 - t0 + 1e-9):.1f}")


def main() -> None:
    p = argparse.ArgumentParser(description="Profiling harness for indexing and queries")
    p.add_argument("--index", help="Path to corpus root folder to build index")
    p.add_argument("--artifacts", help="Path to artifacts file (protobuf)")
    p.add_argument("--queries", help="Path to a queries.txt file", default=None)
    p.add_argument("--k", type=int, default=5, help="Top-k suggestions for query profiling")
    args = p.parse_args()

    if args.index and args.artifacts:
        profile_index(args.index, args.artifacts)
    if args.queries:
        profile_queries(args.queries, k=args.k)


if __name__ == "__main__":
    main()


