# Architecture

## Top-level flow

1. `infoproc process` scans the input path and builds a file index.
2. The scheduler captures an environment snapshot and chooses a batch execution plan.
3. Each file moves through a conversion tree:
   - `00_source`
   - `01_probe`
   - `02_normalized`
   - `03_text_raw`
   - `04_text_clean`
   - `05_final`
4. Final summaries are written under `05_final/_summaries`.

## Key modules

- `src/infoproc/cli.py`: public CLI
- `src/infoproc/config.py`: config loading and `init` file generation
- `src/infoproc/pipeline.py`: discovery, stage execution, manifests, logs
- `src/infoproc/execution.py`: environment snapshot and scheduler plan
- `src/infoproc/services/transcription.py`: media transcription
- `src/infoproc/services/documents.py`: document conversion and text extraction
- `src/infoproc/aggregate.py`: final summary generation

## Output model

Each run is written under:

```text
<storage_root>/runs/<run_name>/
```

The run directory contains:

- stage folders for artifacts
- `_manifests/` for machine-readable run metadata
- `_logs/` for run and per-file logs

## Runtime assumptions

- media transcription may use CUDA when available
- document extraction is CPU-bound
- `distill` and `rank` depend on an OpenAI-compatible HTTP endpoint
