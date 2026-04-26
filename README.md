# infoproc

`infoproc` 是一个面向混合目录的信息加工流水线。它把音视频、纯文本和文档统一扫描成一棵转换树，并把所有中间产物按层级保存下来。

当前版本：`1.0.1`

English version: [README-EN.md](README-EN.md)

## 分发方式

`infoproc` 现在已经是一个标准 Python package，仓库里定义了：

- 模块名：`infoproc`
- 命令名：`infoproc`

但它**当前没有发布到 PyPI**。也就是说，普通用户不能直接执行 `pip install infoproc`，而是通过下面三种方式使用：

1. 从 GitHub clone 源码后执行 `pip install -e .` 或 `pip install .`
2. 安装构建出来的 wheel：`pip install dist/infoproc-1.0.1-py3-none-any.whl`
3. 在 Linux 上使用 rootless bundle：`dist/infoproc-linux-user-1.0.1.tar.gz`

只有在安装完成后，下面两种调用方式才成立：

- `infoproc ...`
- `python -m infoproc ...`

如果只是仓库内部开发调试，也可以临时用 `PYTHONPATH=src python -m infoproc ...`，但这不是给普通用户的推荐路径。

## 用户安装与部署

### 1. 从 GitHub 安装

```bash
git clone https://github.com/wilianyichen/information-process.git
cd information-process
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[media]"
```

如果你要开发或跑测试，再加：

```bash
pip install -e ".[dev]"
```

如果你要启用 `--diarize`，再加：

```bash
pip install -e ".[diarize]"
```

### 2. 初始化配置

```bash
infoproc --config ./config.toml init --storage-root ./outputs
```

### 3. 配置环境变量

至少需要：

```bash
export INFOPROC_API_KEY="replace-me"
export INFOPROC_BASE_URL="https://your-openai-compatible-endpoint/v1"
export INFOPROC_MODEL="astron-code-latest"
```

只有启用 `--diarize` 时才需要：

```bash
export HF_TOKEN="replace-me"
```

### 4. 执行处理

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality
```

如果需要多说话人分离：

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality --diarize
```

### 5. 服务器 git clone 部署

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

然后准备配置：

```bash
sudo mkdir -p /etc/infoproc /var/lib/infoproc/state /var/lib/infoproc/models /var/lib/infoproc/hf_home /srv/infoproc/storage
sudo cp deploy/linux/config.linux.example.toml /etc/infoproc/config.toml
sudo cp deploy/linux/infoproc.env.example /etc/infoproc/infoproc.env
```

再执行：

```bash
.venv/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality
```

## 当前能力

- 音频：`mp3`, `wav`, `m4a`, `flac`, `aac`, `ogg`, `wma`
- 视频：`mp4`, `mov`, `mkv`, `avi`, `webm`, `wmv`, `m4v`
- 直接文本：`txt`, `md`
- 文档：`pdf`, `doc`, `docx`, `ppt`, `pptx`

转换链：

- `video__mp4|mov|... -> audio__wav -> transcript__json + plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `audio__mp3|wav|... -> audio__wav -> transcript__json + plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `plain_text__txt`、`markdown__md -> plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `document__docx -> plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `presentation__pptx -> plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `document__pdf -> plain_text__txt -> clean_text__txt -> distill__md / rank__md`
- `document__doc -> document__docx -> plain_text__txt -> ...`
- `presentation__ppt -> presentation__pptx -> plain_text__txt -> ...`

说明：

- `pdf` 默认先走 `pypdf`，如果抽不出来且系统有 `pdftotext`，会自动回退。
- `doc/ppt` 依赖 `LibreOffice headless` 或 `soffice`。没有该依赖时会明确失败，不会静默透传。
- 最终聚合输出为两个总结文件：`蒸馏与降秩汇总.md` 和 `clean汇总.md`。

## CLI

初始化配置：

```bash
infoproc --config ./config.toml init --storage-root ./outputs
```

处理一个文件或整个目录：

```bash
infoproc --config ./config.toml process --input ./input --recursive --profile quality --diarize
```

预下载模型：

```bash
infoproc --config ./config.toml download-model --profile quality --cache-dir ~/wuxiaoran/models
```

兼容别名仍保留：

- `run --input ... --output ...`
- `batch --input ... --output ... --recursive`

但文档、脚本和 rootless 包都默认使用 `init/process`。

## 输出目录结构

运行时会在 `storage.root_dir/runs/<run_name>/` 下生成一整棵转换树：

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
          蒸馏与降秩汇总.md
          clean汇总.md
      _manifests/
        run_manifest.json
        file_index.json
        scheduler_plan.json
        environment_snapshot.json
      _logs/
        run.log
        files/
```

目录命名同时保留两层语义：

- 一般描述：`video`, `audio`, `document`, `presentation`, `plain_text`, `clean_text`, `distill`, `rank`
- 后缀描述：`mp4`, `wav`, `pdf`, `pptx`, `txt`, `md`, `json`

例如：

- `00_source/video__mp4/demo/lesson.mp4`
- `02_normalized/audio__wav/demo/lesson.wav`
- `03_text_raw/plain_text__txt/demo/lesson.txt`
- `05_final/distill__md/demo/lesson.md`

汇总文件说明：

- `05_final/_summaries/蒸馏与降秩汇总.md`
- `05_final/_summaries/clean汇总.md`

第一个文件会按相对路径汇总全部蒸馏与降秩结果；第二个文件会按相对路径汇总全部 clean 文本。即使某类内容为空，也会写入非空提示，避免出现空白汇总文件。

## 配置

复制 [`config.example.toml`](config.example.toml) 为 `config.toml`，或直接运行 `infoproc init` 生成。

关键配置段：

- `[storage]`：`root_dir`, `runs_dir_name`
- `[scheduler]`：`mode`, `document_workers`, `transcribe_workers`, `llm_workers`
- `[document]`：`pdf_engine`, `office_converter`
- `[transcription]`：模型档位和缓存目录
- `[diarization]`：`HF_TOKEN` 所用目录

配置查找顺序：

1. CLI `--config`
2. `INFOPROC_CONFIG`
3. `./config.toml`
4. `~/.config/infoproc/config.toml`
5. `/etc/infoproc/config.toml`

## 调度策略

默认 `scheduler.mode = "auto"`。

当前策略会先扫描输入目录并生成 `file_index`、`environment_snapshot` 和 `scheduler_plan`，再按资源情况选择执行方式：

- 有 CUDA 时，转写 lane 基本保持单路，优先稳定吃满 GPU
- 文档抽取和纯文本清洗走独立 CPU worker
- `distill/rank` 走独立 LLM worker 池
- 大媒体优先，小文档和纯文本穿插填空
- 内存较紧时会自动退化为更低并发

## 主要实现位置

- CLI：[`src/infoproc/cli.py`](src/infoproc/cli.py)
- 配置：[`src/infoproc/config.py`](src/infoproc/config.py)
- 调度：[`src/infoproc/execution.py`](src/infoproc/execution.py)
- 主流水线：[`src/infoproc/pipeline.py`](src/infoproc/pipeline.py)
- 文档抽取：[`src/infoproc/services/documents.py`](src/infoproc/services/documents.py)
- 最终汇总：[`src/infoproc/aggregate.py`](src/infoproc/aggregate.py)

## 测试

```bash
python -m unittest discover -s tests
```

当前测试覆盖：

- `init/process` CLI 解析
- 配置加载与路径展开
- 转换树输出与最终汇总
- `docx/pptx/pdf` 文本抽取
- 无 LibreOffice 时 `doc/ppt` 的显式失败
- GPU/CPU 调度计划的基础决策

## Rootless Linux 打包

```bash
python -m build
python scripts/build_rootless_bundle.py
```

输出：

- `dist/infoproc-1.0.1.tar.gz`
- `dist/infoproc-1.0.1-py3-none-any.whl`
- `dist/infoproc-linux-user-1.0.1.tar.gz`

rootless 使用方式见 [`deploy/linux/rootless/README.md`](deploy/linux/rootless/README.md)。
