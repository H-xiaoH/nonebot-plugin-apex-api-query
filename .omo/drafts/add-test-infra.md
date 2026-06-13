# Draft: 添加测试基础设施

## Core Objective
为 nonebot-plugin-apex-api-query 建立完整测试基础设施，覆盖全部 7 个源模块，使用 pytest-httpx + nonebug 组合验证现有行为，并集成到 GitHub Actions CI。

## Scope IN
- `tests/conftest.py` — 共享 fixtures，mock 策略，NoneBot 初始化
- `tests/test_data.py` — `convert()` + 常量验证
- `tests/test_config.py` — `api_key_must_not_be_empty` + 默认值
- `tests/test_models.py` — `PlayerStats` 构造
- `tests/test_data_source.py` — 9 个异步函数，两种 HTTP 模式
- `tests/test_storage.py` — `save_record` / `get_latest_record` roundtrip + `format_comparison`
- `tests/test_image.py` — 4 个公开 render 函数 + 纯辅助函数
- `tests/test_handlers.py` — 4 个命令处理器，每种 3 条关键路径（happy path / text-only / API error）
- `.github/workflows/tests.yml` — CI 工作流（Python 3.10/3.11/3.12）
- `pyproject.toml` — `[tool.pytest.ini_options]` + test 依赖组

## Scope OUT
- ❌ 处理器全覆盖（12+ 分支）— 每种只测 3 条关键路径
- ❌ 像素级图片对比 — 只验证返回非空 PNG bytes，不崩溃
- ❌ 独立测试 `_` 前缀的 PIL 内部辅助函数 — 通过公开 render 间接覆盖
- ❌ `logger.exception` 断言 — 脆弱，测试行为（fallback 到了 text）不测日志
- ❌ 基准图对比 — 不创建参考图片
- ❌ 数据库集成测试（真实 SQLite）— 纯 Mock Session
- ❌ 修改 `publish.yml` — 新建独立 `tests.yml`

## Test Strategy
- **Approach**: tests-after（代码已存在，验证现有行为）
- **Agent-executed QA**: 每个任务包含 QA scenario
- **CI**: push + PR 触发，Python 3.10/3.11/3.12

## Import Strategy (Module-Level Side Effects)

`__init__.py:19` `driver = get_driver()` 和 `config.py:34` `config = get_plugin_config(Config)` 在模块导入时执行，需要 NoneBot 运行时。

**解决方式**（nonebug 标准模式）：
1. `conftest.py` → `pytest_configure` hook 设置 `os.environ["APEX_API_KEY"] = "test-key"`
2. `conftest.py` → `pytest_collection_modifyitems` 强制 session 级别事件循环
3. `conftest.py` → `NONEBOT_INIT_KWARGS` 配置 `sqlalchemy_database_url` 和 `alembic_startup_check=False`
4. **所有插件导入必须放在测试函数内部**（不在模块顶层 import）

## DB Mock Strategy (3-Layer Chain)

`storage.py` 使用 `async with get_session() as session:` → `session.execute()` → `result.scalar_one_or_none()`：

```python
# 层1: get_session() → AsyncMock 上下文管理器
mock_session = AsyncMock()
mock_session.execute = AsyncMock()
mock_session.commit = AsyncMock()
mock_session.add = MagicMock()

# 层2: session.execute() → 返回 awaitable Result
mock_result = MagicMock()
mock_result.scalar_one_or_none.return_value = PlayerStats(...)
mock_session.execute.return_value = mock_result

# 层3: async context manager
mock_get_session.return_value.__aenter__.return_value = mock_session
```

## Handler Test Scope (3 Paths Per Handler)

每种处理器只测 3 条关键路径：

| 处理器 | Happy Path | Text-Only Path | Error Path |
|--------|-----------|---------------|------------|
| `apex_player` | 合法玩家名 → API 返回数据 → 图片渲染成功 | `config.apex_only_text=True` → 纯文本输出 | API 返回错误 → 错误消息 |
| `apex_map` | 地图数据 → 图片渲染成功 | `config.apex_only_text=True` | API 错误 |
| `apex_server` | 服务器数据 → 图片渲染成功 | `config.apex_only_text=True` | API 错误 |
| `apex_predator` | 顶猎数据 → 图片渲染成功 | `config.apex_only_text=True` | API 错误 |

## Image Test Scope

4 个公开 render 函数：验证返回非空 PNG bytes + 不崩溃（minimal fixture data）。
3 个纯辅助函数：`_fmt_remaining`（0, -1, 59, 60, 3599, 3600, 3661），`_fmt_num`（0, -1, 100, 1000, 1000000），`_parse_time_str`。

## Test File Location
`tests/` at repo root（标准 Python 项目约定）。

## User Decisions (Confirmed)
- 测试策略：测试后补（代码已存在，验证现有行为）
- 测试框架：pytest-httpx + nonebug 组合（单元 + 集成）
- 范围：全部 7 个模块一把梭
- DB 测试：Mock Session（不依赖真实数据库）
- CI 集成：默认加入（"一把梭全覆盖"）
