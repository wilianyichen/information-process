---
name: infoproc-linux-release
description: Use when working on the infoproc workspace for Linux rootless packaging, WinSCP upload flows, large-v3 predownload into a custom model cache such as ~/wuxiaoran/models, or installing the matching Codex skill so future Codex runs can recognize this release workflow.
---

# infoproc Linux Release

Use this skill for the workspace at `F:\work\information-process` when the task involves packaging, rootless Linux deployment, model predownload, or Codex skill installation.

## Core workflow

1. Read the current product version from `pyproject.toml` and `src/infoproc/__init__.py`.
2. If the user wants a new release artifact, run:
   - `python -m unittest discover -s tests`
   - `python -m build`
   - `python scripts/build_rootless_bundle.py`
3. Use the generated rootless bundle under `dist/infoproc-linux-user-<version>.tar.gz` as the WinSCP upload artifact.

## large-v3 predownload

For this project, `large-v3` is selected by `--profile quality`.

Preferred commands:

```bash
infoproc --config /path/to/config.toml download-model --profile quality --cache-dir ~/wuxiaoran/models
```

For the bundled rootless install:

```bash
bash install.sh --model-cache-dir ~/wuxiaoran/models --prefetch-large-v3
```

Or after installation:

```bash
~/.local/opt/infoproc/bin/download-quality-model.sh ~/wuxiaoran/models
```

## WinSCP delivery

Upload only the rootless bundle tarball to the server user home, then unpack and install:

```bash
cd ~
tar -xzf infoproc-linux-user-<version>.tar.gz
cd infoproc-linux-user-<version>
bash install.sh --model-cache-dir ~/wuxiaoran/models --prefetch-large-v3 --install-codex-skill
```

Installed usage should center on:

```bash
~/.local/opt/infoproc/bin/run-job.sh process --input /data/input --recursive --profile quality
```

## Files to check

- `src/infoproc/aggregate.py`
- `src/infoproc/pipeline.py`
- `src/infoproc/cli.py`
- `src/infoproc/config.py`
- `src/infoproc/services/transcription.py`
- `README.md`
- `README-EN.md`
- `deploy/linux/rootless/README.md`
- `deploy/linux/rootless/README-EN.md`

## Expected artifacts

- `dist/infoproc-<version>.tar.gz`
- `dist/infoproc-<version>-py3-none-any.whl`
- `dist/infoproc-linux-user-<version>.tar.gz`
