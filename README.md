# Autocomplete Text

Fast autocomplete over a large text corpus. Finds sentences containing a word that starts with your prefix (allows one character edit: substitution, insertion, deletion). Results are scored by `scoring.py`.

## Setup

- Python 3.10+
- Install deps:

```bash
pip install -r requirements.txt
```

## Index the corpus

Create the artifacts file from a directory of `.txt` files (or let it auto-detect/extract the provided ZIP):

```bash
python index_app.py --out artifacts.pb
# or explicitly
python index_app.py --index ./Archive --out artifacts.pb
```

## Run the app

```bash
python app.py --artifacts artifacts.pb
```

Type your query and press Enter. Use `#` to quit.

## Tests

```bash
pytest -q
```
