# Linux deployment

This project now deploys as a CLI-first processing tool. It no longer exposes a built-in HTTP API or queue service.

Recommended shape:

- app code and venv: `/opt/infoproc/app`
- config file: `/etc/infoproc/config.toml`
- environment file: `/etc/infoproc/infoproc.env`
- runtime state: `/var/lib/infoproc/state`
- storage root: `/srv/infoproc/storage`
- model cache: `/var/lib/infoproc/models`
- diarization cache: `/var/lib/infoproc/hf_home`

## Install flow

1. Install OS packages:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv ffmpeg
```

2. Copy the repo to `/opt/infoproc/app`.

3. Bootstrap the Python environment:

```bash
cd /opt/infoproc/app
bash scripts/bootstrap_linux.sh
```

4. Copy the sample files:

```bash
sudo mkdir -p /etc/infoproc /var/lib/infoproc/state /var/lib/infoproc/models /var/lib/infoproc/hf_home /srv/infoproc/storage
sudo cp deploy/linux/config.linux.example.toml /etc/infoproc/config.toml
sudo cp deploy/linux/infoproc.env.example /etc/infoproc/infoproc.env
```

5. Fill in the real API key and base URL in `/etc/infoproc/infoproc.env`.

6. Run processing jobs directly or from cron:

```bash
/opt/infoproc/app/.venv/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality
```

## Config precedence

1. CLI `--config`
2. `INFOPROC_CONFIG`
3. `./config.toml`
4. `~/.config/infoproc/config.toml`
5. `/etc/infoproc/config.toml`

## Optional dependencies

- Standard transcription needs `faster-whisper`.
- Diarization needs `torch`, `whisperx`, and `HF_TOKEN`.
- `.doc` / `.ppt` extraction needs LibreOffice headless or `soffice`.

## No-sudo option

If you do not have `sudo`, use the rootless bundle:

- docs: `deploy/linux/rootless/README.md`
- builder: `scripts/build_rootless_bundle.py`
