# 贡献说明

## 开发环境

建议使用 Python `3.11+`。

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pip install -e ".[media]"
```

只有需要 `--diarize` 时再装：

```powershell
pip install -e ".[diarize]"
```

### Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
pip install -e ".[media]"
```

## 测试与构建

```bash
python -m unittest discover -s tests
python -m build
python scripts/build_rootless_bundle.py
```

## 开发约定

- 对外 CLI 以 `init`、`process`、`download-model` 为主
- 不要把运行时密钥提交进仓库
- 改动用户工作流时，要同步更新 `README.md` 和 `docs/`
