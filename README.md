# Autocomplete Text Project (Phase A)

This project indexes a text corpus and provides autocomplete suggestions for input prefixes.

## Features

- Corpus indexing from a directory of `.txt` files or from `students_materials/Archive.zip`
- Normalization (lowercase, punctuation removal, whitespace collapse)
- Exact substring matching over normalized sentences
- Scoring based on query length
- Protobuf-based artifacts for faster, smaller serialization
- Separate apps: `index_app.py` (indexing), `app.py` (query UI)
- Optional auto-reindex when artifacts are missing or stale
- Profiling harness to measure indexing and query performance

## Requirements

- Python 3.10+
- Install deps:

```bash
pip install -r requirements.txt
```

If you see `ModuleNotFoundError: No module named 'google'`, it means the Protobuf runtime is missing in your interpreter. Install it in your active venv:

```bash
pip install --upgrade pip setuptools wheel protobuf
python -c "import google.protobuf; print('ok')"
```

If using PyCharm, ensure you install into the interpreter configured for the project (Settings → Project → Python Interpreter).

## Indexing

You can index from an extracted directory or from the provided ZIP by extracting first, or let the tool auto-detect.

- Using `index_app.py` with a directory:

```bash
python index_app.py --index ./Archive --out artifacts.pb
```

- If you have the ZIP, extract it to a folder (e.g., `./.archive_extracted`) and then index that folder:

```bash
python -c "import zipfile; zipfile.ZipFile('students_materials/Archive.zip').extractall('.archive_extracted')"
python index_app.py --index ./.archive_extracted --out artifacts.pb
```

- Auto-detect source and freshness:

```bash
python index_app.py --out artifacts.pb
# add --force to rebuild regardless of timestamps
```

## Running the UI

`app.py` no longer performs indexing. Ensure you have `artifacts.pb` created by `index_app.py` first, then run:

```bash
python app.py --artifacts artifacts.pb
```

Type your prefix and press Enter. Type `#` to exit.

## Profiling

A simple profiling harness is provided in `profile_harness.py`:

- Measure indexing time for a given corpus
- Measure query throughput on a list of test prefixes

```bash
python profile_harness.py --index ./.archive_extracted --artifacts artifacts.pb --queries queries.txt
```

`queries.txt` should contain one query per line.

## Artifacts Format (Protobuf)

`artifacts.pb` is a serialized protobuf with the following schema (defined dynamically at runtime):

- `sentences_original`: repeated string
- `sentences_norm`: repeated string
- `meta`: repeated message `{ string path; uint32 line_no; }`

Alignment is by index; the i-th elements correspond to the same sentence.

## Development Notes

- The indexing logic is in `indexer.py` and is used by both `index_app.py` (batch) and `app.py` (on-demand rebuild).
- Matching and scoring live in `matcher.py` and `scoring.py`.
- Data structures are defined in `schema.py`.

## Git Hygiene

The following are ignored and must not be committed:

- `artifacts.pb`
- `artifacts.pkl`
- `__pycache__/`
- `*.pyc`
- `.archive_extracted/`

Use `git add -A` responsibly; `.gitignore` covers these paths.
