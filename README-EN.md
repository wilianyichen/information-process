# infoproc

`infoproc` is a mixed-directory information processing pipeline. It scans media, text, and document inputs into one conversion tree and stores every intermediate artifact by stage.

Current version: `1.0.1`

Chinese version: [README.md](README.md)

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
- Final aggregate outputs are split into `蒸馏汇总.md` and `降秩汇总.md`.

## CLI

Initialize config:

```bash
python -m infoproc --config ./config.toml init --storage-root ./outputs
```

Process a file or folder:

```bash
python -m infoproc --config ./config.toml process --input ./input --recursive --profile quality --diarize
```

Pre-download a model:

```bash
python -m infoproc --config ./config.toml download-model --profile quality --cache-dir ~/wuxiaoran/models
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
