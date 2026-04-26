# Deploy

## Recommended server shape

This project is CLI-first. Deploy it as a package plus scheduled or manual `infoproc process` runs.

Suggested directories:

- app: `/opt/infoproc/app`
- config: `/etc/infoproc/config.toml`
- env: `/etc/infoproc/infoproc.env`
- state: `/var/lib/infoproc/state`
- storage: `/srv/infoproc/storage`
- model cache: `/var/lib/infoproc/models`
- diarization cache: `/var/lib/infoproc/hf_home`

## Standard Linux deployment

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv ffmpeg libreoffice
git clone https://github.com/wilianyichen/information-process.git /opt/infoproc/app
cd /opt/infoproc/app
bash scripts/bootstrap_linux.sh
sudo cp deploy/linux/config.linux.example.toml /etc/infoproc/config.toml
sudo cp deploy/linux/infoproc.env.example /etc/infoproc/infoproc.env
```

Edit `/etc/infoproc/infoproc.env` and fill:

- `INFOPROC_API_KEY`
- `INFOPROC_BASE_URL`
- `INFOPROC_MODEL`
- `HF_TOKEN` only when diarization is enabled

Optional model predownload:

```bash
/opt/infoproc/app/.venv/bin/infoproc --config /etc/infoproc/config.toml download-model --profile quality --cache-dir /var/lib/infoproc/models
```

Run a job:

```bash
/opt/infoproc/app/.venv/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality
```

For recurrent execution, wrap that command with `cron` or a `systemd timer`.

## Rootless Linux deployment

Build:

```bash
python -m unittest discover -s tests
python -m build
python scripts/build_rootless_bundle.py
```

Install:

```bash
cd ~
tar -xzf infoproc-linux-user-1.0.1.tar.gz
cd infoproc-linux-user-1.0.1
bash install.sh --model-cache-dir ~/wuxiaoran/models --storage-root ~/infoproc-storage --prefetch-large-v3
```
