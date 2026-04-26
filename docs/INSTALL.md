# 安装说明

## 这个项目现在算不算一个可安装模块？

算，但要把两个层面分开看：

- 从 Python 打包角度看，它已经是一个标准 package
- 从公共分发角度看，它**还没有发布到 PyPI**

仓库里已经定义了：

- 模块名：`infoproc`
- CLI 命令：`infoproc`

所以用户当前的可用安装路径是：

1. `git clone` 后执行 `pip install -e .`
2. 安装构建好的 wheel：`pip install dist/infoproc-1.0.1-py3-none-any.whl`
3. 在 Linux 上使用 rootless bundle：`dist/infoproc-linux-user-1.0.1.tar.gz`

也就是说，`python -m infoproc ...` 和 `infoproc ...` 只有在安装完成后才可用；不能假设用户只是下载源码就能直接运行。

## 本地开发安装

### Windows

```powershell
git clone https://github.com/wilianyichen/information-process.git
cd information-process
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[media]"
```

如果要开发或跑测试，再加：

```powershell
pip install -e ".[dev]"
```

如果要启用 `--diarize`，再加：

```powershell
pip install -e ".[diarize]"
```

初始化配置：

```powershell
infoproc --config .\config.toml init --storage-root .\outputs
```

设置当前会话环境变量：

```powershell
$env:INFOPROC_API_KEY="replace-me"
$env:INFOPROC_BASE_URL="https://your-openai-compatible-endpoint/v1"
$env:INFOPROC_MODEL="astron-code-latest"
```

如果启用 `--diarize`：

```powershell
$env:HF_TOKEN="replace-me"
```

运行：

```powershell
infoproc --config .\config.toml process --input .\input --recursive --profile quality
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

如果要启用 `--diarize`：

```bash
pip install -e ".[diarize]"
```

如果要开发或跑测试：

```bash
pip install -e ".[dev]"
```

初始化配置：

```bash
infoproc --config ./config.toml init --storage-root ./outputs
```

设置环境变量：

```bash
export INFOPROC_API_KEY="replace-me"
export INFOPROC_BASE_URL="https://your-openai-compatible-endpoint/v1"
export INFOPROC_MODEL="astron-code-latest"
```

如果启用 `--diarize`：

```bash
export HF_TOKEN="replace-me"
```

运行：

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality
```

## 系统依赖

- `ffmpeg` 和 `ffprobe`：媒体探测与音频归一化
- `LibreOffice headless` 或 `soffice`：处理 `.doc` / `.ppt`
- `HF_TOKEN`：只有启用 `--diarize` 时需要
