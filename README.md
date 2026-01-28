# AI Flywheel

> 一个通过 AI 飞轮持续自我改进的 Todo CLI 工具

AI Flywheel 是一个实验项目，展示如何让 AI 持续扫描、发现并修复代码问题，形成一个自动进化的编程系统。

## 功能

### Todo CLI 工具

```bash
# 添加待办事项
todo add "Fix login bug" -p high

# 列出待办事项
todo list
todo list --all

# 完成待办事项
todo complete 1

# 删除待办事项
todo delete 1

# 更新待办事项
todo update 1 --title "New title" --priority high
```

### AI 飞轮改进

- **自动扫描** - 每周扫描代码，发现潜在问题
- **智能评估** - 根据严重程度分配优先级 (p0-p3)
- **自动修复** - 按优先级自动修复问题
- **安全回滚** - CI 失败时自动撤销提交

## 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/flywheel.git
cd flywheel

# 安装依赖
uv sync

# 安装命令（可选）
uv pip install -e .
```

## 快速开始

### 使用 Todo CLI

```bash
# 添加任务
todo add "完成项目文档" -p high
todo add "修复登录bug" --tags urgent,bug
todo add "重构存储层" -p medium

# 查看任务
todo list
todo list --status todo
todo list --format json

# 完成任务
todo complete 1

# 删除任务
todo delete 2
```

### 启用 AI 飞轮

在 GitHub 仓库设置中添加 Secret：

| Secret | 值 |
|--------|-----|
| `ANTHROPIC_API_KEY` | 你的 Claude API 密钥 |

推送代码后，AI 飞轮将自动开始工作：

| Workflow | 触发条件 | 功能 |
|----------|----------|------|
| `scan.yml` | 每小时 | 扫描 `src/` 代码创建 Issues |
| `evaluate.yml` | 标签变化 | 重新评估优先级 |
| `fix.yml` | 每 2 小时 | 自动修复问题 |

## 安全性和环境变量

### FLYWHEEL_STRICT_MODE

为了防止在文件锁不可用时发生数据损坏，AI Flywheel 支持严格模式：

```bash
# 启用严格模式（推荐用于生产环境）
export FLYWHEEL_STRICT_MODE=1

# 或使用其他真值
export FLYWHEEL_STRICT_MODE=true
export FLYWHEEL_STRICT_MODE=yes
export FLYWHEEL_STRICT_MODE=on
```

**为什么需要严格模式？**

- **Unix 系统**：如果 `fcntl` 模块不可用（例如 Cygwin），系统会在降级模式下运行，使用文件锁作为后备方案。这可能在高并发场景下导致数据竞争。
- **Windows 系统**：如果 `pywin32` 不可用，系统会使用文件锁作为后备方案。

**严格模式的行为：**

- 启用后，如果最优文件锁不可用（Unix 上是 `fcntl`，Windows 上是 `pywin32`），程序将立即抛出 `RuntimeError` 并退出
- 这可以防止在不知情的情况下运行在降级模式，避免数据损坏风险

**何时使用：**

- ✅ 生产环境推荐启用
- ✅ 多实例部署场景必须启用
- ❌ 开发环境可选（允许降级模式以便在受限环境中测试）
- ❌ 单用户桌面应用可选（并发风险较低）

### 存储延迟指标 (Telemetry)

AI Flywheel 支持通过 StatsD 发送存储延迟指标，用于监控 I/O 性能和识别潜在瓶颈：

```bash
# 配置 StatsD 服务器
export FW_STATSD_HOST=localhost
export FW_STATSD_PORT=8125  # 可选，默认 8125
```

**指标说明：**

- `flywheel.storage.load.latency` - 文件加载操作延迟（毫秒）
- `flywheel.storage.save.latency` - 文件保存操作延迟（毫秒）
- `flywheel.storage.acquire_file_lock.latency` - 文件锁获取延迟（毫秒）

**使用场景：**

- 🔍 **性能监控** - 跟踪 I/O 操作响应时间
- 🐛 **问题诊断** - 识别慢速存储或锁竞争
- 📊 **容量规划** - 了解负载模式，优化资源配置
- 🎯 **优化验证** - 量化性能改进效果

**注意事项：**

- 如果未配置 `FW_STATSD_HOST`，指标功能自动禁用，不影响正常运行
- 需要安装 `statsd` Python 包：`pip install statsd`
- 指标发送失败不会影响主要功能的执行

## 项目结构

```
flywheel/
├── src/flywheel/        # Todo CLI 工具（被 AI 改进的目标）
│   ├── cli.py           # 命令行接口
│   ├── storage.py       # 数据存储
│   ├── formatter.py     # 输出格式化
│   └── todo.py          # 数据模型
├── scripts/             # AI 飞轮脚本
│   ├── scan.py          # 代码扫描器
│   ├── evaluate.py      # 优先级评估器
│   └── fix.py           # 自动修复器
├── tests/               # 测试用例
├── .github/workflows/   # GitHub Actions
└── docs/                # 设计文档
```

## 优先级系统

AI 通过 5 个标签管理问题优先级：

| 标签 | 说明 | 响应时间 |
|------|------|----------|
| `p0` | 紧急 - 安全漏洞、数据丢失 | 立即 |
| `p1` | 高 - 核心功能受损 | 6 小时内 |
| `p2` | 中 - 一般问题、优化 | 24 小时内 |
| `p3` | 低 - 代码规范、文档 | 按需 |
| `frozen` | 冻结 - 暂停 AI 操作 | 需人工介入 |

## 人工控制

```bash
# 调整问题优先级
gh issue edit 42 --remove-label p2 --add-label p0

# 冻结所有问题
gh issue list --state open | jq '.[].number' | xargs -I {} gh issue edit {} --add-label frozen

# 查看 AI 提交
git log --author="AI Flywheel" --oneline -10
```

## 飞轮改进示例

| 第 1 周 | 第 2 周 | 第 3 周 | 第 4 周 |
|---------|---------|---------|---------|
| 基础 add/list | 添加 due date | 优先级排序 | 彩色输出 |
| 基本测试覆盖 | 修复 bug | 性能优化 | 添加 filter |
| ... | AI 发现重复代码 | AI 重构 | AI 添加搜索 |

## 本地开发

```bash
# 运行测试
uv run pytest --cov=src

# 代码检查
uv run ruff check .
uv run ruff format .

# 手动触发扫描
MAX_ISSUES=5 TARGET_DIR=src uv run python scripts/scan.py

# 手动触发修复
MAX_FIXES=3 CI_TIMEOUT=1800 uv run python scripts/fix.py
```

## 设计文档

| 文档 | 说明 |
|------|------|
| [工作流程](./docs/workflow.md) | **TDD 修复流程和 Commit 规范** |
| [PRD](./docs/prd.md) | 产品需求文档 |
| [架构设计](./docs/arch.md) | 系统架构和技术方案 |
| [Claude API](./docs/claude-api.md) | API 集成调研 |

## 许可证

MIT License
