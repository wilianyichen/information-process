# Install

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
python -m infoproc --config .\config.toml init --storage-root .\outputs
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
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
pip install -e ".[media]"
```

Optional diarization support:

```bash
pip install -e ".[diarize]"
```

## System dependencies

- `ffmpeg` and `ffprobe` for media normalization and probing
- `LibreOffice headless` or `soffice` for `.doc` / `.ppt`
- `HF_TOKEN` only when `--diarize` is enabled
