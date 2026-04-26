# Linux 部署说明

这个项目现在是 CLI-first 工具，不再对外暴露内置 HTTP API。

`infoproc` 已经是一个可安装的 Python package，但**还没有发布到 PyPI**。所以服务器上的标准使用方式是：

- clone GitHub 仓库
- 创建 venv
- 用 `pip install -e .` 从源码安装
- 执行 `infoproc process ...`

## 推荐目录

- 应用代码和 venv：`/opt/infoproc/app`
- 配置文件：`/etc/infoproc/config.toml`
- 环境变量文件：`/etc/infoproc/infoproc.env`
- 状态目录：`/var/lib/infoproc/state`
- 保存目录：`/srv/infoproc/storage`
- 模型缓存：`/var/lib/infoproc/models`
- diarization 缓存：`/var/lib/infoproc/hf_home`

## 安装流程

### 1. 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv ffmpeg libreoffice
```

### 2. clone 仓库

```bash
git clone https://github.com/wilianyichen/information-process.git /opt/infoproc/app
```

### 3. 初始化 Python 环境

```bash
cd /opt/infoproc/app
bash scripts/bootstrap_linux.sh
```

### 4. 复制配置样例

```bash
sudo mkdir -p /etc/infoproc /var/lib/infoproc/state /var/lib/infoproc/models /var/lib/infoproc/hf_home /srv/infoproc/storage
sudo cp deploy/linux/config.linux.example.toml /etc/infoproc/config.toml
sudo cp deploy/linux/infoproc.env.example /etc/infoproc/infoproc.env
```

### 5. 填写环境变量

编辑 `/etc/infoproc/infoproc.env`，补齐：

- `INFOPROC_API_KEY`
- `INFOPROC_BASE_URL`
- `INFOPROC_MODEL`

如果启用 `--diarize`，再补：

- `HF_TOKEN`

### 6. 执行任务

```bash
/opt/infoproc/app/.venv/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality
```

## 无 sudo 场景

如果没有 `sudo`，用 rootless bundle：

- 文档：`deploy/linux/rootless/README.md`
- 打包脚本：`scripts/build_rootless_bundle.py`
