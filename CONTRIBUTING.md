# Contributing

## Development setup

Use Python `3.11+`.

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pip install -e ".[media]"
```

Only install diarization dependencies when needed:

```powershell
pip install -e ".[diarize]"
```

### Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
pip install -e ".[media]"
```

## Test and build

```bash
python -m unittest discover -s tests
python -m build
python scripts/build_rootless_bundle.py
```

## Coding notes

- keep the public CLI centered on `init`, `process`, and `download-model`
- keep runtime secrets out of the repository and use environment variables instead
- prefer updating docs under `README.md` and `docs/` whenever user-facing behavior changes
