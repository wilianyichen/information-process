# Rootless Linux Deployment

This bundle targets Linux environments without `sudo` or systemd requirements. Everything stays inside a user-owned install directory.

Current version: `1.0.1`

Chinese version: [README.md](README.md)

## What this bundle exposes

- `infoproc init` for config generation
- `infoproc process` for mixed-folder processing
- `download-quality-model.sh` for prefetching `large-v3`

It no longer exposes a local HTTP API workflow.

## Requirements

- `python3`
- `python3 -m venv`
- `ffmpeg` and `ffprobe` on `PATH`, or copied into `<install-root>/tools/ffmpeg/bin`

Optional but important:

- LibreOffice headless / `soffice` for `.doc` and `.ppt`
- `HF_TOKEN` plus `--with-whisperx` if you want diarization

## Build and upload

```bash
python -m unittest discover -s tests
python -m build
python scripts/build_rootless_bundle.py
```

Bundle output:

```text
dist/infoproc-linux-user-1.0.1.tar.gz
```

## Install on the server

```bash
cd ~
tar -xzf infoproc-linux-user-1.0.1.tar.gz
cd infoproc-linux-user-1.0.1
bash install.sh --model-cache-dir ~/wuxiaoran/models --prefetch-large-v3 --install-codex-skill
```

Optional flags:

- `--root <path>`
- `--storage-root <path>`
- `--model-cache-dir <path>`
- `--no-faster-whisper`
- `--with-whisperx`
- `--prefetch-large-v3`
- `--install-codex-skill`

## Common commands

Download the quality model:

```bash
~/.local/opt/infoproc/bin/download-quality-model.sh ~/wuxiaoran/models
```

Interactive folder processing:

```bash
~/.local/opt/infoproc/bin/process-multimodal-folder.sh
```

Direct CLI usage:

```bash
~/.local/opt/infoproc/bin/run-job.sh process --input /data/input --recursive --profile quality --diarize
```
