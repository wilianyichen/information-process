# Rootless Linux 部署说明

这个 bundle 面向没有 `sudo`、不想碰 systemd、只想在用户目录内运行 `infoproc` 的场景。

当前版本：`1.0.1`

English version: [README-EN.md](README-EN.md)

## 目标

安装后默认使用：

- `infoproc init` 生成配置
- `infoproc process` 处理混合目录
- `download-quality-model.sh` 单独下载 `large-v3`

对外不再暴露本地 HTTP API。

## 前提

- Linux 用户可执行 `python3`
- Linux 用户可执行 `python3 -m venv`
- `ffmpeg` / `ffprobe` 在系统 `PATH` 上，或你自己放到 `<install-root>/tools/ffmpeg/bin`

如果你要处理 `.doc` / `.ppt`，还需要：

- `LibreOffice headless` 或 `soffice`

如果你要启用 `--diarize`：

- `HF_TOKEN`
- 安装时加 `--with-whisperx`

## 打包

```bash
python -m unittest discover -s tests
python -m build
python scripts/build_rootless_bundle.py
```

输出：

```text
dist/infoproc-linux-user-1.0.1.tar.gz
```

## WinSCP 上传与服务器安装

```bash
cd ~
tar -xzf infoproc-linux-user-1.0.1.tar.gz
cd infoproc-linux-user-1.0.1
bash install.sh --model-cache-dir ~/wuxiaoran/models --prefetch-large-v3 --install-codex-skill
```

可选安装参数：

- `--root <path>`：指定安装根目录
- `--storage-root <path>`：指定默认保存根目录
- `--model-cache-dir <path>`：指定模型缓存目录
- `--no-faster-whisper`：跳过安装 `faster-whisper`
- `--with-whisperx`：安装 `whisperx`
- `--prefetch-large-v3`：安装后立即下载 quality 模型
- `--install-codex-skill`：安装 bundle 内置 skill

## 安装后目录

默认安装到：

```text
$HOME/.local/opt/infoproc
```

核心路径：

- 配置：`$INSTALL_ROOT/config/config.toml`
- 环境变量：`$INSTALL_ROOT/config/infoproc.env`
- 保存根目录：`$INSTALL_ROOT/storage`
- 模型缓存：`$INSTALL_ROOT/models`

## 常用命令

下载 quality 模型：

```bash
~/.local/opt/infoproc/bin/download-quality-model.sh ~/wuxiaoran/models
```

交互式选择目录并处理：

```bash
~/.local/opt/infoproc/bin/process-multimodal-folder.sh
```

直接跑 CLI：

```bash
~/.local/opt/infoproc/bin/run-job.sh process --input /data/input --recursive --profile quality --diarize
```

## Codex skill

安装完成后也可以单独执行：

```bash
~/.local/opt/infoproc/bin/install-codex-skill.sh
```

当前 bundle 安装两个 skill：

- `infoproc-linux-release`
- `infoproc-multimodal-processing`
