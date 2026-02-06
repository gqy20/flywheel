# Flywheel Todo CLI

> 一个轻量的 Todo 命令行工具，聚焦本地任务管理与稳健存储。

## 功能

- 添加、查看、更新、完成、删除待办事项
- 多种输出格式（含 JSON）
- 文件锁与安全兜底
- 可选 StatsD 存储性能指标

## 安装

```bash
git clone https://github.com/your-username/flywheel.git
cd flywheel
uv sync
uv pip install -e .  # 可选：安装 todo 命令
```

## 快速开始

```bash
# 添加
todo add "Fix login bug" -p high
todo add "Write docs" --tags docs,urgent

# 查看
todo list
todo list --all
todo list --format json

# 更新/完成/删除
todo update 1 --title "New title" --priority medium
todo complete 1
todo delete 1
```

## 安全与配置

### `FLYWHEEL_STRICT_MODE`

推荐生产环境开启，防止在锁能力降级时继续运行：

```bash
export FLYWHEEL_STRICT_MODE=1
```

### StatsD 指标（可选）

```bash
export FW_STATSD_HOST=localhost
export FW_STATSD_PORT=8125
```

指标包括：

- `flywheel.storage.load.latency`
- `flywheel.storage.save.latency`
- `flywheel.storage.acquire_file_lock.latency`

## 本地开发

```bash
# 测试
uv run pytest --cov=src

# 代码质量
uv run ruff check .
uv run ruff format .

# 扫描脚本（本地）
MAX_ISSUES=5 TARGET_DIR=src uv run python scripts/scan.py

# 文档同步校验
uv run python scripts/check_docs_sync.py --check
```

## 项目结构

```text
flywheel/
├── src/flywheel/        # Todo CLI 核心实现
├── scripts/             # 自动化脚本
├── tests/               # 测试
├── .github/workflows/   # CI / 自动化工作流
└── docs/                # 设计文档
```

## 飞轮自动化说明

飞轮（Issue 整理、并行修复候选、PR 仲裁合并）文档在：

- `.github/FLYWHEEL.md`
- 文档门禁与自动维护 workflow：`docs-ci.yml`、`docs-auto-maintenance.yml`

## 文档

- `.github/FLYWHEEL.md`（飞轮自动化策略与运行说明）
- `docs/claude-api.md`（Claude API 调研）
- `docs/generated/workflow-inputs.md`（workflow_dispatch 参数自动生成索引）
- `docs/runbook.md`（自动化运行与故障处置手册）

## 许可证

MIT License
