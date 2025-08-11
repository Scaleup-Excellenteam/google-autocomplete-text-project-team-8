from __future__ import annotations
from typing import Iterable, Tuple, Optional
import bisect

from schema import IndexArtifacts, Match
from utils import norm
_ws_by_char: dict[str, list[tuple[int, int]]] = {}
_ws_all: list[tuple[int, int]] = []
_inv_tokens_sorted: list[str] = []
_inv_postings_by_token: dict[str, list[tuple[int, int]]] = {}

# Result-capped scanning to bound worst-case latency (~2s target)
_MAX_UNIQUE_SENTENCES: int = 10000
_MAX_POSTINGS_PER_TOKEN: int = 5000


def set_word_starts(ws_list: list[tuple[int, int]], sentences_norm: list[str]) -> None:
    """Provide precomputed word starts from artifacts to speed up matching.
    ws_list contains (sentence_id, pos) pairs in normalized coordinates.
    """
    global _ws_by_char, _ws_all
    _ws_by_char = {}
    _ws_all = list(ws_list)
    for sid, pos in ws_list:
        try:
            ch = sentences_norm[sid][pos]
        except Exception:
            continue
        bucket = _ws_by_char.setdefault(ch, [])
        bucket.append((sid, pos))


def set_inverted_index(inv_index: dict[str, list[tuple[int, int]]]) -> None:
    """Initialize the in-memory inverted index structures.
    inv_index maps token -> list of (sentence_id, pos) where token starts at pos in normalized sentence.
    """
    global _inv_tokens_sorted, _inv_postings_by_token
    _inv_postings_by_token = inv_index or {}
    _inv_tokens_sorted = sorted(_inv_postings_by_token.keys())
import re
from scoring import score_match


def _match_prefix_exact(sentence_norm: str, query_norm: str) -> bool:
    if not query_norm:
        return False
    return sentence_norm.startswith(query_norm)


def _original_offset(sentence_original: str, query_norm: str) -> int:
    """
    Mapping normalized window back to original; for POC do a casefolded literal search.
    This may be off when punctuation breaks alignment.
    """
    low = sentence_original.casefold()
    j = low.find(query_norm)
    return j if j >= 0 else 0


def _norm_with_positions(s: str) -> Tuple[str, list[int]]:
    """
    Normalize string the same way as utils.norm, but also return a mapping from
    normalized index to original index. Whitespace runs collapse to one space
    and map to the first whitespace's original index. Punctuation is removed.
    """
    if not s:
        return "", []
    # mirror utils.norm: remove punctuation, casefold, collapse spaces
    # We'll build incrementally to also track positions
    out_chars: list[str] = []
    out_pos: list[int] = []
    prev_ws = False
    for idx, ch in enumerate(s):
        # treat alnum and underscore as word, whitespace as space, others dropped
        if ch.isalnum() or ch == "_":
            out_chars.append(ch.casefold())
            out_pos.append(idx)
            prev_ws = False
        elif ch.isspace():
            if not prev_ws:
                out_chars.append(" ")
                out_pos.append(idx)
            prev_ws = True
        else:
            # punctuation removed
            continue
    # trim leading/trailing spaces
    # adjust positions accordingly: if leading space exists, drop it
    if out_chars and out_chars[0] == " ":
        out_chars.pop(0)
        out_pos.pop(0)
    if out_chars and out_chars[-1] == " ":
        out_chars.pop()
        out_pos.pop()
    return ("".join(out_chars), out_pos)


def _best_prefix_anywhere(sentence_norm: str, query_norm: str) -> Optional[Tuple[str, int, int]]:
    """
    Find the best match where query_norm matches a prefix of sentence_norm starting at some offset.
    Returns (kind, pos1, start_idx) where kind in {"exact","sub","ins","del"}.
    Preference order: exact > sub > indel. First occurrence wins per kind.
    """
    qlen = len(query_norm)
    slen = len(sentence_norm)
    if qlen == 0 or slen == 0 or slen < min(qlen - 1, 0):
        return None

    # Compute word starts (positions at 0 or preceded by space)
    starts: list[int] = []
    prev_space = True
    for idx, ch in enumerate(sentence_norm):
        if prev_space and ch != ' ':
            starts.append(idx)
        prev_space = (ch == ' ')

    # Exact prefix at word starts
    for j in starts:
        if j + qlen <= slen and sentence_norm.startswith(query_norm, j):
            return ("exact", 0, j)

    # One substitution at word starts
    if slen >= qlen:
        for j in starts:
            if j + qlen > slen:
                continue
            mismatches = 0
            pos1 = 0
            seg = sentence_norm[j : j + qlen]
            for i, (a, b) in enumerate(zip(seg, query_norm)):
                if a != b:
                    mismatches += 1
                    pos1 = i + 1
                    if mismatches > 1:
                        break
            if mismatches == 1:
                return ("sub", pos1, j)

    # One deletion (sentence has extra char): compare windows of length qlen+1
    if slen >= qlen + 1:
        for j in starts:
            if j + qlen + 1 > slen:
                continue
            i = 0  # query index
            k = 0  # sentence window index
            skipped = False
            while i < qlen and k < qlen + 1:
                if query_norm[i] == sentence_norm[j + k]:
                    i += 1
                    k += 1
                elif not skipped:
                    skipped = True
                    k += 1
                else:
                    break
            if i == qlen:
                pos1 = i + 1 if skipped else qlen
                return ("del", max(1, pos1), j)

    # One insertion (query has extra char): compare windows of length qlen-1
    if qlen >= 2 and slen >= qlen - 1:
        for j in starts:
            if j + (qlen - 1) > slen:
                continue
            i = 0  # query index
            k = 0  # sentence window index
            skipped = False
            pos1 = 0
            while i < qlen and k < qlen - 1:
                if query_norm[i] == sentence_norm[j + k]:
                    i += 1
                    k += 1
                elif not skipped:
                    skipped = True
                    pos1 = i + 1
                    i += 1
                else:
                    break
            if k == qlen - 1 and (i == qlen or (not skipped and i + 1 == qlen)):
                return ("ins", max(1, pos1 or qlen), j)

    return None


def _best_prefix_at(sentence_norm: str, query_norm: str, j: int) -> Optional[Tuple[str, int, int]]:
    qlen = len(query_norm)
    slen = len(sentence_norm)
    if qlen == 0 or j < 0 or j >= slen:
        return None

    # Exact
    if j + qlen <= slen and sentence_norm.startswith(query_norm, j):
        return ("exact", 0, j)

    # Substitution
    if j + qlen <= slen:
        mismatches = 0
        pos1 = 0
        seg = sentence_norm[j : j + qlen]
        for i, (a, b) in enumerate(zip(seg, query_norm)):
            if a != b:
                mismatches += 1
                pos1 = i + 1
                if mismatches > 1:
                    break
        if mismatches == 1:
            return ("sub", pos1, j)

    # Deletion (sentence has extra char)
    if j + qlen + 1 <= slen:
        i = 0
        k = 0
        skipped = False
        while i < qlen and k < qlen + 1:
            if query_norm[i] == sentence_norm[j + k]:
                i += 1
                k += 1
            elif not skipped:
                skipped = True
                k += 1
            else:
                break
        if i == qlen:
            pos1 = i + 1 if skipped else qlen
            return ("del", max(1, pos1), j)

    # Insertion (query has extra char)
    if qlen >= 2 and j + (qlen - 1) <= slen:
        i = 0
        k = 0
        skipped = False
        pos1 = 0
        while i < qlen and k < qlen - 1:
            if query_norm[i] == sentence_norm[j + k]:
                i += 1
                k += 1
            elif not skipped:
                skipped = True
                pos1 = i + 1
                i += 1
            else:
                break
        if k == qlen - 1 and (i == qlen or (not skipped and i + 1 == qlen)):
            return ("ins", max(1, pos1 or qlen), j)
    return None


def _match_prefix_one_sub(sentence_norm: str, query_norm: str) -> Tuple[bool, int]:
    """
    Allow exactly one substitution within the first len(query_norm) characters.
    Returns (matched, pos1) where pos1 is 1-based index in query where edit occurred.
    """
    qlen = len(query_norm)
    if len(sentence_norm) < qlen or qlen == 0:
        return (False, 0)
    mismatches = 0
    pos1 = 0
    for i in range(qlen):
        if sentence_norm[i] != query_norm[i]:
            mismatches += 1
            if mismatches > 1:
                return (False, 0)
            pos1 = i + 1
    return ((mismatches == 1), pos1)


def _match_prefix_one_indel(sentence_norm: str, query_norm: str) -> Tuple[bool, str, int]:
    """
    Allow exactly one insertion or deletion across the prefix.
    Returns (matched, kind, pos1) where kind in {"ins","del"} from the perspective of the query:
    - kind == "ins": query has one extra char (query longer by 1)
    - kind == "del": query has one missing char (sentence longer by 1)
    pos1 is 1-based index in the query where the edit occurred.
    """
    qlen = len(query_norm)
    slen = len(sentence_norm)
    if qlen == 0:
        return (False, "ins", 0)

    # Case A: sentence has one extra char at the start-prefix compared to query (query missing one)
    if slen >= qlen + 1:
        i = j = 0  # i->query, j->sentence
        skipped = False
        while i < qlen and j < slen:
            if query_norm[i] == sentence_norm[j]:
                i += 1
                j += 1
                continue
            if skipped:
                break
            # skip one in sentence (query missing this char)
            skipped = True
            j += 1
        if i == qlen:
            # edit position is at the point in query where skip happened
            pos1 = i + 1 if skipped and j <= slen else qlen
            return (True, "del", max(1, pos1))

    # Case B: query has one extra char compared to sentence (need to skip one in query)
    if qlen == slen + 1:
        i = j = 0
        skipped = False
        pos1 = 0
        while i < qlen and j < slen:
            if query_norm[i] == sentence_norm[j]:
                i += 1
                j += 1
                continue
            if skipped:
                break
            skipped = True
            pos1 = i + 1
            i += 1  # skip a char in query
        # If remaining chars align or we've reached ends appropriately
        if (j == slen and (i == qlen or (not skipped and i + 1 == qlen))) or (i == qlen and j == slen):
            return (True, "ins", max(1, pos1 or qlen))

    return (False, "ins", 0)


def find_matches(query: str, art: IndexArtifacts) -> Iterable[Match]:
    qn = norm(query)
    if not qn:
        return []
    yielded_sids: set[int] = set()
    yielded_count = 0

    # Prefer inverted index when available: prefix range over sorted tokens
    if _inv_tokens_sorted:
        # Find token range with prefix qn
        # If qn contains spaces, only use the first token as prefix anchor
        prefix = qn.split(" ")[0]
        if not prefix:
            return []
        lo = bisect.bisect_left(_inv_tokens_sorted, prefix)
        hi = bisect.bisect_right(_inv_tokens_sorted, prefix + "\uffff")
        produced_any = False
        # Iterate tokens in lexicographic order (already ensured by _inv_tokens_sorted)
        for tok in _inv_tokens_sorted[lo:hi]:
            postings = _inv_postings_by_token.get(tok, [])
            # Postings may be large for frequent tokens; after compaction we have at most one pos per sentence
            scanned_this_token = 0
            for sid, j in postings:
                if scanned_this_token >= _MAX_POSTINGS_PER_TOKEN:
                    break
                scanned_this_token += 1
                if sid in yielded_sids:
                    continue
                s_norm = art.sentences_norm[sid]
                best = _best_prefix_at(s_norm, qn, j)
                if not best:
                    continue
                kind, pos1, start_idx = best
                score = score_match(qn, kind if kind in ("exact", "sub", "ins", "del") else "exact", (pos1 or None))
                _, positions = _norm_with_positions(art.sentences_original[sid])
                off = positions[start_idx] if 0 <= start_idx < len(positions) else 0
                yield Match(
                    sentence_id=sid,
                    sentence_original=art.sentences_original[sid],
                    sentence_norm=s_norm,
                    offset=off,
                    score=score,
                    meta=art.meta[sid],
                )
                produced_any = True
                yielded_sids.add(sid)
                yielded_count += 1
                if yielded_count >= _MAX_UNIQUE_SENTENCES:
                    return
        if produced_any:
            return
        # No exact-prefix candidates via inverted index → fall back to 1-edit at token level then word-start
        # Token-level 1-edit: generate variants and scan their postings
        alphabet: set[str] = set()
        for tok in _inv_tokens_sorted[lo:hi]:
            alphabet.update(tok)
        # If prefix is common ASCII, seed alphabet to letters+digits to avoid empty set
        if not alphabet:
            alphabet = set("abcdefghijklmnopqrstuvwxyz0123456789_")

        variants: set[str] = set()
        L = len(prefix)
        # substitutions
        for i in range(L):
            for ch in alphabet:
                if ch == prefix[i]:
                    continue
                variants.add(prefix[:i] + ch + prefix[i+1:])
        # deletions
        for i in range(L):
            variants.add(prefix[:i] + prefix[i+1:])
        # insertions
        for i in range(L + 1):
            for ch in alphabet:
                variants.add(prefix[:i] + ch + prefix[i:])

        produced = False
        for var in sorted(variants):
            lo2 = bisect.bisect_left(_inv_tokens_sorted, var)
            hi2 = bisect.bisect_right(_inv_tokens_sorted, var)
            for tok in _inv_tokens_sorted[lo2:hi2]:
                postings2 = _inv_postings_by_token.get(tok, [])
                scanned_this_token = 0
                for sid, j in postings2:
                    if scanned_this_token >= _MAX_POSTINGS_PER_TOKEN:
                        break
                    scanned_this_token += 1
                    if sid in yielded_sids:
                        continue
                    s_norm = art.sentences_norm[sid]
                    best = _best_prefix_at(s_norm, qn, j)
                    if not best:
                        continue
                    kind, pos1, start_idx = best
                    score = score_match(qn, kind if kind in ("exact", "sub", "ins", "del") else "exact", (pos1 or None))
                    _, positions = _norm_with_positions(art.sentences_original[sid])
                    off = positions[start_idx] if 0 <= start_idx < len(positions) else 0
                    yield Match(
                        sentence_id=sid,
                        sentence_original=art.sentences_original[sid],
                        sentence_norm=s_norm,
                        offset=off,
                        score=score,
                        meta=art.meta[sid],
                    )
                    produced = True
                    yielded_sids.add(sid)
                    yielded_count += 1
                    if yielded_count >= _MAX_UNIQUE_SENTENCES:
                        return
        if produced:
            return

    # Fallback path (and default when no inverted index):
    # Use precomputed word-start buckets to allow 1-edit at the prefix
    primary_starts: list[tuple[int, int]]
    fallback_starts: list[tuple[int, int]] = []
    if _ws_by_char:
        ch0 = qn[0]
        primary_starts = _ws_by_char.get(ch0, [])
        # Fallback for first-char substitution: try other buckets but cap the scan size
        for ch, lst in _ws_by_char.items():
            if ch == ch0:
                continue
            fallback_starts.extend(lst)
            # no hard cap to preserve result ordering per user's request
    else:
        # No precomputed starts; fallback to per-sentence scanning
        for sid, s_norm in enumerate(art.sentences_norm):
            if yielded_count >= _MAX_UNIQUE_SENTENCES:
                return
            best = _best_prefix_anywhere(s_norm, qn)
            if not best:
                continue
            kind, pos1, start_idx = best
            score = score_match(qn, kind if kind in ("exact", "sub", "ins", "del") else "exact", (pos1 or None))
            _, positions = _norm_with_positions(art.sentences_original[sid])
            off = positions[start_idx] if 0 <= start_idx < len(positions) else 0
            yield Match(
                sentence_id=sid,
                sentence_original=art.sentences_original[sid],
                sentence_norm=s_norm,
                offset=off,
                score=score,
                meta=art.meta[sid],
            )
            yielded_count += 1
        return

    # Evaluate candidates from precomputed starts
    def eval_starts(starts: list[tuple[int, int]]):
        nonlocal yielded_count, yielded_sids
        for sid, j in starts:
            if yielded_count >= _MAX_UNIQUE_SENTENCES:
                return
            if sid in yielded_sids:
                continue
            s_norm = art.sentences_norm[sid]
            best = _best_prefix_at(s_norm, qn, j)
            if not best:
                continue
            kind, pos1, start_idx = best
            score = score_match(qn, kind if kind in ("exact", "sub", "ins", "del") else "exact", (pos1 or None))
            _, positions = _norm_with_positions(art.sentences_original[sid])
            off = positions[start_idx] if 0 <= start_idx < len(positions) else 0
            yield Match(
                sentence_id=sid,
                sentence_original=art.sentences_original[sid],
                sentence_norm=s_norm,
                offset=off,
                score=score,
                meta=art.meta[sid],
            )
            yielded_sids.add(sid)
            yielded_count += 1

    # First pass: same first-char bucket
    for m in eval_starts(primary_starts):
        yield m
    # Second pass: fallback for first-char substitution
    for m in eval_starts(fallback_starts):
        yield m
