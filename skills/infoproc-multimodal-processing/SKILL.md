---
name: infoproc-multimodal-processing
description: Use when working on the infoproc workspace for multimodal information processing, especially selecting an input folder, running whisperx diarization for multiple speakers, converting media to text, and generating distill plus rank outputs from a mixed directory.
---

# infoproc Multimodal Processing

Use this skill for the workspace at `F:\work\information-process` when the user wants the actual multimodal processing workflow rather than release packaging.

## What this skill covers

- choose an input folder manually
- process mixed directories of audio, video, text, and documents
- use `whisperx` diarization with multi-speaker separation
- transcribe or extract text
- clean the text
- generate distill and rank outputs
- use run-scoped conversion trees plus final summaries under `05_final/_summaries`

## Preferred execution path

For installed rootless environments, prefer the bundled interactive script:

```bash
~/.local/opt/infoproc/bin/process-multimodal-folder.sh
```

That script:

- prompts for the input folder manually
- optionally prompts for a run name
- runs `process --recursive`
- forces `--diarize`
- forces `--profile quality`
- forces `--distill both`

## Prerequisites

- `whisperx` must be installed in the active infoproc venv
- `HF_TOKEN` must be set
- `ffmpeg` and `ffprobe` must be available
- `transcription.quality_model` should stay `large-v3` unless the user explicitly changes it

## Direct command

If the user does not want the interactive script, use:

```bash
infoproc --config /path/to/config.toml process --input /path/in --recursive --profile quality --diarize --distill both
```

## Files to inspect

- `src/infoproc/cli.py`
- `src/infoproc/pipeline.py`
- `src/infoproc/aggregate.py`
- `src/infoproc/services/transcription.py`
- `deploy/linux/rootless/bin/process-multimodal-folder.sh`

## Outputs to expect

- run-scoped conversion tree under `storage.root_dir/runs/<run-name>/`
- `05_final/_summaries/蒸馏汇总.md`
- `05_final/_summaries/降秩汇总.md`
