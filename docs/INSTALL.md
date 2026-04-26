# Install

## Is this already a publishable module?

Yes, in the Python packaging sense. This repository defines:

- module: `infoproc`
- command: `infoproc`

No, in the package-index sense. It is **not published to PyPI yet**. Users currently install it from source, from a built wheel, or from the rootless bundle.

Supported installation paths:

1. `git clone` + `pip install -e .`
2. `pip install dist/infoproc-1.0.1-py3-none-any.whl`
3. `dist/infoproc-linux-user-1.0.1.tar.gz`

## Local development

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pip install -e ".[media]"
```

Optional diarization support:

```powershell
pip install -e ".[diarize]"
```

Initialize config:

```powershell
infoproc --config .\config.toml init --storage-root .\outputs
```

Set environment variables for the current session:

```powershell
$env:INFOPROC_API_KEY="replace-me"
$env:INFOPROC_BASE_URL="https://your-openai-compatible-endpoint/v1"
$env:INFOPROC_MODEL="astron-code-latest"
```

Optional:

```powershell
$env:HF_TOKEN="replace-me"
```

### Linux

```bash
git clone https://github.com/wilianyichen/information-process.git
cd information-process
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[media]"
```

Optional diarization support:

```bash
pip install -e ".[diarize]"
```

Optional development extras:

```bash
pip install -e ".[dev]"
```

Initialize config:

```bash
infoproc --config ./config.toml init --storage-root ./outputs
```

Run:

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality
```

## System dependencies

- `ffmpeg` and `ffprobe` for media normalization and probing
- `LibreOffice headless` or `soffice` for `.doc` / `.ppt`
- `HF_TOKEN` only when `--diarize` is enabled
