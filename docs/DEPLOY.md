# 部署说明

## 推荐部署形态

这个项目现在是 CLI-first，不是常驻 API 服务。推荐把它部署成：

- 一份源码或安装后的 Python 环境
- 一份配置文件
- 一条手工执行或定时执行的 `infoproc process` 命令

建议目录：

- 应用目录：`/opt/infoproc/app`
- 配置文件：`/etc/infoproc/config.toml`
- 环境变量文件：`/etc/infoproc/infoproc.env`
- 运行状态目录：`/var/lib/infoproc/state`
- 输出保存目录：`/srv/infoproc/storage`
- 模型缓存目录：`/var/lib/infoproc/models`
- diarization 缓存目录：`/var/lib/infoproc/hf_home`

## 标准 Linux 部署

### 1. 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv ffmpeg libreoffice
```

### 2. clone 仓库

```bash
git clone https://github.com/wilianyichen/information-process.git /opt/infoproc/app
cd /opt/infoproc/app
```

### 3. 初始化 Python 环境

```bash
bash scripts/bootstrap_linux.sh
```

### 4. 准备配置目录

```bash
sudo mkdir -p /etc/infoproc /var/lib/infoproc/state /var/lib/infoproc/models /var/lib/infoproc/hf_home /srv/infoproc/storage
sudo cp deploy/linux/config.linux.example.toml /etc/infoproc/config.toml
sudo cp deploy/linux/infoproc.env.example /etc/infoproc/infoproc.env
```

### 5. 填写环境变量

编辑 `/etc/infoproc/infoproc.env`，至少补这三个值：

- `INFOPROC_API_KEY`
- `INFOPROC_BASE_URL`
- `INFOPROC_MODEL`

只有启用 `--diarize` 时才需要：

- `HF_TOKEN`

### 6. 可选预下载模型

```bash
/opt/infoproc/app/.venv/bin/infoproc --config /etc/infoproc/config.toml download-model --profile quality --cache-dir /var/lib/infoproc/models
```

### 7. 执行处理任务

```bash
/opt/infoproc/app/.venv/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality
```

如果需要多说话人分离：

```bash
/opt/infoproc/app/.venv/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality --diarize
```

## 定时执行建议

如果要周期性跑任务，建议外层用：

- `cron`
- `systemd timer`

当前不建议把它包装成常驻服务，因为它的核心工作流是“按批次处理输入目录”，不是长期监听请求。

## Rootless Linux 部署

如果没有 `sudo` 权限，使用 rootless bundle：

```bash
python -m unittest discover -s tests
python -m build
python scripts/build_rootless_bundle.py
```

安装：

```bash
cd ~
tar -xzf infoproc-linux-user-1.0.1.tar.gz
cd infoproc-linux-user-1.0.1
bash install.sh --model-cache-dir ~/wuxiaoran/models --storage-root ~/infoproc-storage --prefetch-large-v3
```
