# 架构说明

## 顶层流程

1. `infoproc process` 扫描输入路径，生成 `file_index`
2. 调度器记录 `environment_snapshot`，再生成 `scheduler_plan`
3. 每个文件按转换树逐层产生产物：
   - `00_source`
   - `01_probe`
   - `02_normalized`
   - `03_text_raw`
   - `04_text_clean`
   - `05_final`
4. 最终汇总文件写入 `05_final/_summaries`

## 关键模块

- `src/infoproc/cli.py`：CLI 入口
- `src/infoproc/config.py`：配置加载和 `init` 配置生成
- `src/infoproc/pipeline.py`：扫描、阶段执行、manifest 和日志写入
- `src/infoproc/execution.py`：环境快照和调度计划
- `src/infoproc/services/transcription.py`：音视频转写
- `src/infoproc/services/documents.py`：文档转换与正文抽取
- `src/infoproc/aggregate.py`：最终汇总生成

## 输出模型

每次运行都写入：

```text
<storage_root>/runs/<run_name>/
```

其中包含：

- 各阶段的产物目录
- `_manifests/`：机器可读的运行元数据
- `_logs/`：总日志和逐文件日志

## 运行时假设

- 媒体转写在有 CUDA 时会优先使用 GPU
- 文档抽取主要是 CPU 负载
- `distill` 和 `rank` 依赖一个 OpenAI-compatible HTTP 接口
