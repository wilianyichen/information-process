# infoproc

`infoproc` is a mixed-directory information processing pipeline. It scans media, text, and document inputs into one conversion tree and stores every intermediate artifact by stage.

Current version: `1.0.1`

Chinese version: [README.md](README.md)

## Distribution

`infoproc` is already structured as a standard Python package. The repository defines:

- module name: `infoproc`
- CLI command: `infoproc`

It is **not published to PyPI yet**. Users cannot install it today with `pip install infoproc`. The supported paths are:

1. clone the GitHub repository and run `pip install -e .` or `pip install .`
2. install the built wheel: `pip install dist/infoproc-1.0.1-py3-none-any.whl`
3. use the Linux rootless bundle: `dist/infoproc-linux-user-1.0.1.tar.gz`

Only after installation will these work:

- `infoproc ...`
- `python -m infoproc ...`

For repository development only, `PYTHONPATH=src python -m infoproc ...` is possible, but that is not the recommended end-user path.

## Install and deploy

### 1. Install from GitHub

```bash
git clone https://github.com/wilianyichen/information-process.git
cd information-process
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[media]"
```

For development and tests:

```bash
pip install -e ".[dev]"
```

For diarization:

```bash
pip install -e ".[diarize]"
```

### 2. Initialize config

```bash
infoproc --config ./config.toml init --storage-root ./outputs
```

### 3. Set runtime environment variables

```bash
export INFOPROC_API_KEY="replace-me"
export INFOPROC_BASE_URL="https://your-openai-compatible-endpoint/v1"
export INFOPROC_MODEL="astron-code-latest"
```

Only for diarization:

```bash
export HF_TOKEN="replace-me"
```

### 4. Run processing

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality
```

For speaker diarization:

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality --diarize
```

### 5. Server deployment from git clone

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv ffmpeg libreoffice
git clone https://github.com/wilianyichen/information-process.git
cd information-process
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[media]"
```

Then prepare config:

```bash
sudo mkdir -p /etc/infoproc /var/lib/infoproc/state /var/lib/infoproc/models /var/lib/infoproc/hf_home /srv/infoproc/storage
sudo cp deploy/linux/config.linux.example.toml /etc/infoproc/config.toml
sudo cp deploy/linux/infoproc.env.example /etc/infoproc/infoproc.env
```

Run with:

```bash
.venv/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality
```

## Supported inputs

- audio: `mp3`, `wav`, `m4a`, `flac`, `aac`, `ogg`, `wma`
- video: `mp4`, `mov`, `mkv`, `avi`, `webm`, `wmv`, `m4v`
- direct text: `txt`, `md`
- documents: `pdf`, `doc`, `docx`, `ppt`, `pptx`

Main conversion chains:

- `video__* -> audio__wav -> transcript__json + plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `audio__* -> audio__wav -> transcript__json + plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `plain_text__txt` and `markdown__md -> plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `document__docx`, `presentation__pptx`, `document__pdf -> plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `document__doc -> document__docx -> ...`
- `presentation__ppt -> presentation__pptx -> ...`

Notes:

- PDFs use `pypdf` first and fall back to `pdftotext` when available.
- Legacy `.doc` / `.ppt` require LibreOffice headless or `soffice`.
- Final aggregate outputs are split into `蒸馏与降秩汇总.md` and `clean汇总.md`.

## CLI

Initialize config:

```bash
infoproc --config ./config.toml init --storage-root ./outputs
```

Process a file or folder:

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality --diarize
```

Pre-download a model:

```bash
infoproc --config ./config.toml download-model --profile quality --cache-dir ~/wuxiaoran/models
```

Compatibility aliases still exist:

- `run --input ... --output ...`
- `batch --input ... --output ... --recursive`

## Output tree

Each run is written under `storage.root_dir/runs/<run_name>/`:

```text
<storage_root>/
  runs/
    <run_id>__<input_root_name>/
      00_source/
      01_probe/
      02_normalized/
      03_text_raw/
      04_text_clean/
      05_final/
        distill__md/
        rank__md/
        _summaries/
      _manifests/
      _logs/
```

Directory names preserve both:

- generic labels such as `video`, `audio`, `document`, `presentation`, `plain_text`, `clean_text`, `distill`, `rank`
- extension labels such as `mp4`, `wav`, `pdf`, `pptx`, `txt`, `md`, `json`

## Config

Copy [config.example.toml](config.example.toml) or generate one with `infoproc init`.

Key sections:

- `[storage]`: `root_dir`, `runs_dir_name`
- `[scheduler]`: `mode`, `document_workers`, `transcribe_workers`, `llm_workers`
- `[document]`: `pdf_engine`, `office_converter`
- `[transcription]`: model profiles and cache directory
- `[diarization]`: diarization token/home settings

## Scheduling

With `scheduler.mode = "auto"`, `infoproc` writes `file_index`, `environment_snapshot`, and `scheduler_plan`, then chooses a runtime shape based on available resources:

- serialize or nearly serialize transcription when CUDA is present
- overlap document extraction and plain text cleanup on CPU workers
- stream cleaned text into dedicated LLM workers for distill/rank
- prioritize larger media first and use smaller docs/text to fill gaps
- reduce parallelism automatically when memory is tight

## Main implementation files

- CLI: [`src/infoproc/cli.py`](src/infoproc/cli.py)
- config: [`src/infoproc/config.py`](src/infoproc/config.py)
- scheduling: [`src/infoproc/execution.py`](src/infoproc/execution.py)
- pipeline: [`src/infoproc/pipeline.py`](src/infoproc/pipeline.py)
- document extraction: [`src/infoproc/services/documents.py`](src/infoproc/services/documents.py)
- aggregate summaries: [`src/infoproc/aggregate.py`](src/infoproc/aggregate.py)

## Tests

```bash
python -m unittest discover -s tests
```

## Rootless Linux packaging

```bash
python -m build
python scripts/build_rootless_bundle.py
```

Outputs:

- `dist/infoproc-1.0.1.tar.gz`
- `dist/infoproc-1.0.1-py3-none-any.whl`
- `dist/infoproc-linux-user-1.0.1.tar.gz`

See [`deploy/linux/rootless/README.md`](deploy/linux/rootless/README.md) for the rootless deployment flow.
