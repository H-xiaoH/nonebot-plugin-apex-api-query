# 添加测试基础设施

## TL;DR

> **Quick Summary**: 使用 pytest-httpx + nonebug 覆盖全部 7 个源模块，建立 conftest.py + 单元测试 + 集成测试 + GitHub Actions CI。
>
> **Deliverables**:
> - `tests/conftest.py` — 共享 fixtures + mock 策略
> - `tests/test_data.py`, `tests/test_config.py`, `tests/test_models.py`
> - `tests/test_data_source.py`, `tests/test_storage.py`
> - `tests/test_image.py`, `tests/test_handlers.py`
> - `.github/workflows/tests.yml` — CI 矩阵（Python 3.10/3.11/3.12）
> - `pyproject.toml` — `[tool.pytest.ini_options]` + test 依赖组
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 5 waves, 最高 5 并行
> **Critical Path**: Wave 1 (conftest + deps) → Wave 2 (全面并行) → Wave 5 (CI)

---

## Context

### Original Request
为 nonebot-plugin-apex-api-query 添加测试基础设施。这是一 个 8 文件的 NoneBot2 插件，查询 Apex Legends API 并渲染图片卡片，当前没有任何测试。

### Interview Summary
**Key Discussions**:
- **测试策略**: 测试后补（代码已存在，验证现有行为）
- **测试框架**: pytest + pytest-httpx + nonebug 组合（单元 + 集成测试）
- **范围**: 全部 7 个模块一把梭
- **DB 测试**: 纯 Mock Session（不依赖真实数据库）
- **处理器测试**: 每种 3 条关键路径（happy / text-only / API error）
- **图片测试**: 验证返回非空 PNG bytes + 不崩溃

**Research Findings**:
- **Module-level side effects**: `__init__.py` 在导入时执行 `get_driver()`, `require()`, `on_alconna()` — 需要 nonebug conftest 初始化
- **Two API endpoints**: mozambiquehe.re 和 apexlegendsstatus.com 使用不同 HTTP 模式，需分开测
- **DB mock chain**: 3 层深度（`get_session()` → async context manager → `execute()` → `scalar_one_or_none()`）
- **Image caches**: `image.py` 有 3 个模块级全局变量（`_image_cache`, `_font_cache`, `_map_cache_dir`），测试间需重置

### Metis Review
**Identified Gaps** (addressed):
- **Import strategy**: 使用 nonebug 标准模式 — `pytest_configure` hook + 测试函数内导入
- **Handler combinatorics**: 限制每种处理器 3 条关键路径，不追求全覆盖
- **Image scope**: 公开函数返回 bytes + 不崩溃；纯辅助函数测试边界值
- **Scope creep locked down**: 不测 logger 调用、不测像素对比、不创建参考图片

---

## Work Objectives

### Core Objective
建立覆盖全部 7 个源模块的测试基础设施，使用 pytest-httpx + nonebug 组合验证现有行为，并集成到 GitHub Actions CI。

### Concrete Deliverables
- `tests/conftest.py` — 共享 fixtures（NoneBot 初始化，httpx mock，DB session mock，image cache 重置）
- `pyproject.toml` 新增 `[tool.pytest.ini_options]` + `[tool.poetry.group.test.dependencies]`
- `tests/test_data.py` — `convert()` + 常量验证
- `tests/test_config.py` — `api_key_must_not_be_empty` + 默认值
- `tests/test_models.py` — `PlayerStats` 构造
- `tests/test_data_source.py` — 9 个异步函数（两种 HTTP 模式），每种 happy + 1 error
- `tests/test_storage.py` — `save_record`/`get_latest_record` roundtrip + `format_comparison`
- `tests/test_image.py` — 4 个 render 函数 + 3 个纯辅助函数
- `tests/test_handlers.py` — 4 个处理器，每种 3 条路径
- `.github/workflows/tests.yml` — CI 矩阵测试

### Definition of Done
- [ ] `poetry run pytest tests/ -v` → 全部通过，0 失败
- [ ] `poetry run pytest tests/ --cov=nonebot_plugin_apex_api_query --cov-report=term` → 输出覆盖率报告
- [ ] GitHub Actions CI 绿色通过（Python 3.10/3.11/3.12）

### Must Have
- `conftest.py` 在 `pytest_configure` hook 设置 `APEX_API_KEY` 环境变量
- 所有插件导入放在测试函数内部（NoneBot 延迟加载）
- pytest-httpx mock 两种 API URL 模式（mozambiquehe.re + apexlegendsstatus.com）
- DB session mock 实现 3 层 async chain
- 处理器测试覆盖 3 条关键路径（happy / text-only / API error）
- 图片 render 测试验证返回非空 PNG bytes
- 4 种错误处理模式覆盖：HTTPError / non-200 / JSONDecodeError / render exception → text fallback
- 纯函数全覆盖边界值：`convert`, `_to_int`, `_to_int_optional`, `_fmt_remaining`, `_fmt_num`, `format_comparison`
- CI 独立 workflow（`tests.yml`），不修改 publish.yml

### Must NOT Have
- ❌ 模块顶层 `from nonebot_plugin_apex_api_query import ...`（导入必须在函数内）
- ❌ 处理器全路径覆盖（12+ 分支）— 每种只测 3 条
- ❌ 像素级图片对比 — 只验证 bytes + 不崩溃
- ❌ 独立测试 `_` 前缀 PIL 内部函数 — 通过公开 render 间接覆盖
- ❌ `logger.exception` 断言 — 测行为（fallback text），不测日志
- ❌ 基准参考图片 — 不创建基准图对比
- ❌ 修改 `publish.yml` — 新建独立 `tests.yml`
- ❌ 真实 SQLite 数据库 — 纯 Mock Session
- ❌ 参考 `he0119/nonebot-plugin-user` 的 DB 清理模式（MySQL/PostgreSQL reset）— 本项目不适用

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO（当前无任何测试）
- **Automated tests**: Tests-after（验证现有行为）
- **Framework**: pytest + pytest-asyncio + pytest-httpx + pytest-mock + pytest-cov + nonebug
- **Agent-executed QA**: ALL tasks include QA scenarios

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.omo/evidence/task-{N}-{scenario-slug}.txt`.

- **Pure functions**: Use Bash (`poetry run pytest tests/test_xxx.py`)
- **API/Backend tests**: Use Bash (curl/pytest output assertion)
- **CI validation**: Use Bash (check workflow YAML syntax)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - foundation):
├── Task 1: 安装 test 依赖 + pyproject.toml [quick]
└── Task 2: tests/conftest.py [deep]

Wave 2 (After Wave 1 - 常量 + 纯函数，全部并行):
├── Task 3: tests/test_data.py [quick]
├── Task 4: tests/test_config.py [quick]
├── Task 5: tests/test_models.py [quick]
├── Task 6: tests/test_image.py (pure helpers) [unspecified-low]
└── Task 7: tests/test_storage.py (format_comparison) [unspecified-low]

Wave 3 (After Wave 1 - API + DB + Image，需要 mock fixtures):
├── Task 8: tests/test_data_source.py [deep]
├── Task 9: tests/test_storage.py (DB roundtrip) [deep]
└── Task 10: tests/test_image.py (render functions) [deep]

Wave 4 (After Wave 3 - handlers integration, depends on all mocks):
├── Task 11: tests/test_handlers.py (apex_player) [deep]
├── Task 12: tests/test_handlers.py (apex_map + apex_server + apex_predator) [deep]

Wave 5 (After Wave 4 - CI + verification):
├── Task 13: .github/workflows/tests.yml [quick]
└── Task 14: Full test suite run + coverage [quick]

Critical Path: Task 2 → Task 8/9/10 → Task 11/12 → Task 13 → Task 14
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 2)
```

### Agent Dispatch Summary

- **1**: **2** — T1 → `quick`, T2 → `deep`
- **2**: **5** — T3 → `quick`, T4 → `quick`, T5 → `quick`, T6 → `unspecified-low`, T7 → `unspecified-low`
- **3**: **3** — T8 → `deep`, T9 → `deep`, T10 → `deep`
- **4**: **2** — T11 → `deep`, T12 → `deep`
- **5**: **2** — T13 → `quick`, T14 → `quick`

---

## TODOs

- [x] 1. Install test dependencies + configure pyproject.toml

  **What to do**:
  - Run: `poetry add --group dev pytest pytest-asyncio pytest-httpx pytest-mock pytest-cov nonebug`
  - Add `[tool.pytest.ini_options]` to pyproject.toml:
    ```toml
    [tool.pytest.ini_options]
    asyncio_mode = "auto"
    asyncio_default_fixture_loop_scope = "session"
    addopts = ["--import-mode=importlib"]
    ```
  - Verify: `poetry run pytest --version` works

  **Must NOT do**:
  - Do NOT add `freezegun` (not needed)
  - Do NOT add `pytest-xdist` (complicates session scope)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single shell command + TOML block insert
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2 — but Task 2 needs deps first, so sequential within wave)
  - **Blocks**: Task 2
  - **Blocked By**: None

  **References**:
  - `pyproject.toml:1-39` — Current config, append after line 39
  - Metis finding: `asyncio_mode = "auto"` + `asyncio_default_fixture_loop_scope = "session"` from nonebot.dev testing docs

  **Acceptance Criteria**:
  - [ ] `poetry add --group dev ...` succeeds, no dependency conflicts
  - [ ] `[tool.pytest.ini_options]` section exists in pyproject.toml
  - [ ] `poetry run pytest --version` outputs version ≥ 8.0
  - [ ] `poetry show pytest-asyncio` shows installed

  **QA Scenarios**:

  ```
  Scenario: All test deps install cleanly
    Tool: Bash
    Preconditions: Poetry virtual env active, pyproject.toml at root
    Steps:
      1. poetry add --group dev pytest pytest-asyncio pytest-httpx pytest-mock pytest-cov nonebug
      2. poetry run pytest --version
    Expected Result: Command exits 0, outputs pytest version ≥ 8.x
    Evidence: .omo/evidence/task-1-deps-install.txt

  Scenario: pytest.ini_options configured correctly
    Tool: Bash
    Preconditions: pyproject.toml updated
    Steps:
      1. grep -A3 "tool.pytest" pyproject.toml
      2. poetry run pytest --co  (collect-only, dry run)
    Expected Result: grep shows asyncio_mode="auto", pytest --co exits 0 (even with 0 tests)
    Evidence: .omo/evidence/task-1-pytest-config.txt
  ```

  **Commit**: NO (groups with Task 2)

- [x] 2. Create tests/conftest.py with NoneBot initialization + shared fixtures

  **What to do**:
  - Create `tests/__init__.py` (empty)
  - Create `tests/conftest.py`:
    1. `pytest_configure` hook: set `os.environ["APEX_API_KEY"] = "test-key"`, `config.stash[NONEBOT_INIT_KWARGS] = {"sqlalchemy_database_url": "sqlite+aiosqlite://", "alembic_startup_check": False}`
    2. `pytest_collection_modifyitems`: force session loop scope for all async tests
    3. Session-scoped autouse fixture `after_nonebot_init`: register adapter + load plugins
    4. `httpx_mock` fixture configuration (auto-use, mock both API URLs)
    5. `mock_db_session` fixture: 3-layer async chain returning configurable scalar results
    6. `reset_image_caches` autouse fixture (if testing image.py): clear `_image_cache`, `_font_cache`, reset `_map_cache_dir`
  - Follow patterns from he0119/nonebot-plugin-user conftest.py

  **Must NOT do**:
  - Do NOT import any plugin module at module level in conftest.py
  - Do NOT register real adapters (use Console adapter for tests)
  - Do NOT forget `asyncio_mode = "auto"` in collection modifier

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires understanding of nonebot module-loading side effects, async context managers, pytest hook lifecycle — easy to get wrong
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (after Task 1 completes)
  - **Parallel Group**: Wave 1 (sole task after deps)
  - **Blocks**: Tasks 3-14 (all tests depend on conftest)
  - **Blocked By**: Task 1

  **References**:
  - `nonebot_plugin_apex_api_query/__init__.py:19` — `driver = get_driver()` (module-level side effect)
  - `nonebot_plugin_apex_api_query/config.py:34` — `config = get_plugin_config(Config)` (module-level side effect)
  - `nonebot_plugin_apex_api_query/config.py:10-13` — Config field defaults (needed for mock overrides)
  - `nonebot_plugin_apex_api_query/storage.py:31-38` — `get_session()` usage pattern (3-layer async chain to mock)
  - `nonebot_plugin_apex_api_query/image.py:91-93` — Module-level caches to reset
  - Librarian finding: he0119/nonebot-plugin-user conftest.py — official nonebot testing pattern reference
  - Metis directive: `pytest_configure` MUST set `APEX_API_KEY` before collection, imports inside test functions

  **Acceptance Criteria**:
  - [ ] `tests/conftest.py` exists with all 5 sections
  - [ ] `pytest_configure` hook sets env + NONEBOT_INIT_KWARGS
  - [ ] `pytest_collection_modifyitems` forces session loop for async tests
  - [ ] `mock_db_session` fixture returns 3-layer mock chain
  - [ ] `reset_image_caches` fixture is autouse
  - [ ] `poetry run pytest --co tests/` collects without import errors

  **QA Scenarios**:

  ```
  Scenario: conftest.py loads without import errors
    Tool: Bash
    Preconditions: Task 1 complete, test deps installed
    Steps:
      1. poetry run pytest tests/ --co  (collect only)
    Expected Result: Exits 0, no ImportError, no ModuleNotFoundError
    Evidence: .omo/evidence/task-2-conftest-load.txt

  Scenario: APEX_API_KEY env var is set before test collection
    Tool: Bash
    Preconditions: conftest.py created
    Steps:
      1. poetry run python -c "import os; print(os.environ.get('APEX_API_KEY', 'NOT SET'))"
    Expected Result: Does NOT print 'NOT SET' when run via pytest (pytest_configure sets it)
    Alternative: create a one-line test that asserts os.environ["APEX_API_KEY"] == "test-key"
    Evidence: .omo/evidence/task-2-api-key-env.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `test: add test infrastructure foundation`
  - Files: `pyproject.toml`, `poetry.lock`, `tests/__init__.py`, `tests/conftest.py`

- [x] 3. Write tests/test_data.py — convert() and constants

  **What to do**:
  - Create `tests/test_data.py`
  - Test `convert()` function from `nonebot_plugin_apex_api_query.data`:
    - Known key → returns Chinese translation (e.g., `convert("Kings Canyon")` → `"诸王峡谷"`)
    - Unknown key → returns original key (e.g., `convert("not_exist")` → `"not_exist"`)
    - None input → returns None
    - Empty string → returns empty string
    - Integer key → translates via BOOLEAN_TRANSLATIONS (0→"否", 1→"是")
    - String boolean → translates ("true"→"是", "false"→"否")
  - Test VALID_PLATFORMS constant: contains ["PC", "PS4", "X1", "SWITCH"]
  - Test DEFAULT_PLATFORM: equals "PC"

  **Must NOT do**:
  - Do NOT audit all translation dictionaries for completeness
  - Do NOT test TRANSLATIONS merge order (implementation detail)
  - Do NOT import at module level; import inside test function

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure functions, zero mocking, straightforward assertions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4-7)
  - **Blocks**: Nothing
  - **Blocked By**: Task 2 (conftest)

  **References**:
  - `nonebot_plugin_apex_api_query/data.py:320-329` — `convert()` implementation
  - `nonebot_plugin_apex_api_query/data.py:3-5` — VALID_PLATFORMS + DEFAULT_PLATFORM
  - `nonebot_plugin_apex_api_query/data.py:297-302` — BOOLEAN_TRANSLATIONS

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_data.py -v` → all tests pass
  - [ ] `convert("Kings Canyon")` test returns "诸王峡谷"
  - [ ] `convert("nonexistent_key")` test returns "nonexistent_key"
  - [ ] `convert(None)` test returns None
  - [ ] `convert(1)` test returns "是"
  - [ ] VALID_PLATFORMS length test passes

  **QA Scenarios**:

  ```
  Scenario: All data.py tests pass
    Tool: Bash
    Preconditions: conftest.py exists, test deps installed
    Steps:
      1. poetry run pytest tests/test_data.py -v --tb=short
    Expected Result: ≥8 tests pass, 0 failures
    Evidence: .omo/evidence/task-3-data-tests.txt
  ```

  **Commit**: NO (groups with Wave 2 batch)

- [x] 4. Write tests/test_config.py — Config validation

  **What to do**:
  - Create `tests/test_config.py`
  - Test `Config.api_key_must_not_be_empty` validator:
    - Empty string → raises `MissingAPIKeyError`
    - Valid key → returns key unchanged
    - Whitespace-only string → passes (current behavior, document as edge case)
  - Test default values:
    - `apex_api_url` defaults to `"https://api.mozambiquehe.re"`
    - `apex_map_api_url` defaults to `"https://api.apexlegendsstatus.com"`
    - `apex_only_text` defaults to `False`

  **Must NOT do**:
  - Do NOT test `get_plugin_config` (requires NoneBot runtime → integration test scope)
  - Do NOT try to mock `nonebot.get_plugin_config` (unit test Config directly)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pydantic model validation, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3,5-7)
  - **Blocks**: Nothing
  - **Blocked By**: Task 2

  **References**:
  - `nonebot_plugin_apex_api_query/config.py:5-31` — Config model + validator

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_config.py -v` → all pass
  - [ ] `Config(apex_api_key="")` raises MissingAPIKeyError
  - [ ] `Config(apex_api_key="valid")` succeeds
  - [ ] Default values test passes

  **QA Scenarios**:

  ```
  Scenario: Config validation tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_config.py -v --tb=short
    Expected Result: ≥5 tests pass, 0 failures
    Evidence: .omo/evidence/task-4-config-tests.txt
  ```

  **Commit**: NO

- [x] 5. Write tests/test_models.py — PlayerStats construction

  **What to do**:
  - Create `tests/test_models.py`
  - Test `PlayerStats` can be constructed with valid fields:
    - `uid="test-uid"`, `player_name="test-player"`, `platform="PC"`, `level=500`, `rank_score=12000`, `rank_name="Diamond"`, `rank_div=2`
  - Test `rank_div` is nullable (accepts None)
  - Test `created_at` can be set explicitly

  **Must NOT do**:
  - Do NOT test table creation / migrations (outside unit test scope)
  - Do NOT test database connection (requires real DB)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple ORM model field test
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 2

  **References**:
  - `nonebot_plugin_apex_api_query/models.py:10-24` — PlayerStats model

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_models.py -v` → all pass
  - [ ] Construction with all fields succeeds
  - [ ] Nullable rank_div test passes

  **QA Scenarios**:

  ```
  Scenario: Models tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_models.py -v --tb=short
    Expected Result: ≥3 tests pass, 0 failures
    Evidence: .omo/evidence/task-5-models-tests.txt
  ```

  **Commit**: NO

- [x] 6. Write tests/test_image.py — pure helper functions

  **What to do**:
  - Create `tests/test_image.py`
  - Test `_fmt_remaining` from `nonebot_plugin_apex_api_query.image`:
    - `_fmt_remaining(0)` → `"00:00"`
    - `_fmt_remaining(-1)` → `"00:00"`
    - `_fmt_remaining(59)` → `"00:59"`
    - `_fmt_remaining(60)` → `"01:00"`
    - `_fmt_remaining(3599)` → `"59:59"`
    - `_fmt_remaining(3600)` → `"01:00:00"`
    - `_fmt_remaining(3661)` → `"01:01:01"`
  - Test `_fmt_num`:
    - `_fmt_num(0)` → `"暂无"`
    - `_fmt_num(-1)` → `"暂无"`
    - `_fmt_num(100)` → `"100"`
    - `_fmt_num(1000)` → `"1,000"`
    - `_fmt_num(1000000)` → `"1,000,000"`
  - Test `_parse_time_str`:
    - `_parse_time_str("2026-06-14 12:30:45")` → `"12:30"`
    - `_parse_time_str("12:30")` → `"12:30"` (single part)

  **Must NOT do**:
  - Do NOT test `_draw_*` or `_gradient_overlay` functions (tested via render functions in Task 10)
  - Do NOT test `_load_font` (requires font file, fragile)
  - Do NOT test `_download_image` (does real HTTP)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Pure functions with edge cases, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 2

  **References**:
  - `nonebot_plugin_apex_api_query/image.py:122-130` — `_fmt_remaining`
  - `nonebot_plugin_apex_api_query/image.py:475-477` — `_fmt_num`
  - `nonebot_plugin_apex_api_query/image.py:237-240` — `_parse_time_str`

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_image.py -v -k "fmt_remaining or fmt_num or parse_time"` → all pass
  - [ ] `_fmt_remaining(3661)` returns `"01:01:01"` (HH boundary)
  - [ ] `_fmt_num(0)` returns `"暂无"`

  **QA Scenarios**:

  ```
  Scenario: Image pure helper tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_image.py -v -k "fmt_remaining or fmt_num or parse_time" --tb=short
    Expected Result: ≥9 tests pass, 0 failures
    Evidence: .omo/evidence/task-6-image-helpers.txt
  ```

  **Commit**: NO

- [x] 7. Write tests/test_storage.py — format_comparison and PlayerStatsData

  **What to do**:
  - Create `tests/test_storage.py`
  - Test `PlayerStatsData` dataclass construction
  - Test `_rank_name`:
    - With `rank_div=2` → `"Diamond 2"`
    - With `rank_div=None` → `"Diamond"`
  - Test `format_comparison` (pure function, no mock needed):
    - All stats identical → empty dict
    - Level up (+3) → `{"等级": "(↑3)"}`
    - Level down (-2) → `{"等级": "(↓2)"}`
    - Score up (+500) → `{"大逃杀分数": "(↑500)"}`
    - Score down (-100) → `{"大逃杀分数": "(↓100)"}`
    - Rank changed → `{"大逃杀段位": "(old_name)"}`
    - Multiple changes simultaneously
    - Zero diff (no change entry)

  **Must NOT do**:
  - Do NOT test `get_latest_record` / `save_record` here (requires DB mock, in Task 9)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Pure functions with combinatorics, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 2

  **References**:
  - `nonebot_plugin_apex_api_query/storage.py:10-16` — PlayerStatsData
  - `nonebot_plugin_apex_api_query/storage.py:70-74` — `_rank_name`
  - `nonebot_plugin_apex_api_query/storage.py:77-109` — `format_comparison`

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_storage.py -v -k "PlayerStatsData or rank_name or format_comparison"` → all pass
  - [ ] All diff combinations tested (≥8 test cases)

  **QA Scenarios**:

  ```
  Scenario: Storage pure function tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_storage.py -v -k "PlayerStatsData or rank_name or format_comparison" --tb=short
    Expected Result: ≥8 tests pass, 0 failures
    Evidence: .omo/evidence/task-7-storage-pure.txt
  ```

  **Commit**: YES (Wave 2 batch)
  - Message: `test: add pure function tests`
  - Files: `tests/test_data.py`, `tests/test_config.py`, `tests/test_models.py`, `tests/test_image.py`, `tests/test_storage.py`

- [x] 8. Write tests/test_data_source.py — API client tests (Pattern A + B)

  **What to do**:
  - Create `tests/test_data_source.py`
  - Use `httpx_mock` fixture from pytest-httpx to intercept all HTTP calls
  - Test Pattern A functions (use `query_apex_api`/`_fetch`):
    - `_fetch("bridge", ...)` happy: mock 200 + valid JSON → returns parsed dict
    - `_fetch("bridge", ...)` HTTPError → raises `ApexAPIError("查询失败: 网络请求错误")`
    - `_fetch("bridge", ...)` non-200 → raises `ApexAPIError(response.text)`
    - `_fetch("bridge", ...)` invalid JSON → raises `ApexAPIError("查询失败: API 返回数据格式错误")`
    - `get_player_stats("player", "PC")` happy: mock full response → returns (formatted text, raw dict)
    - `get_player_stats("player", "PC")` API error → returns (error string, None)
    - `get_map_rotation()` happy: mock map data → returns formatted text
    - `get_server_status_data()` happy: mock all sections → returns list[dict]
    - `get_predator_data()` happy: mock RP data → returns dict
  - Test Pattern B (`get_map_rotation_data` — DIFFERENT error handling):
    - `get_map_rotation_data()` happy: mock apexlegendsstatus.com → returns dict
    - `get_map_rotation_data()` HTTPError → returns `"地图查询失败: 网络请求错误"` (string, NOT exception)
    - `get_map_rotation_data()` non-200 → returns `"地图查询失败: {status_code}"` (string)
    - `get_map_rotation_data()` invalid JSON → returns `"地图查询失败: API 返回数据格式错误"` (string)

  **Must NOT do**:
  - Do NOT make real HTTP requests (all mocked via httpx_mock)
  - Do NOT test `_format_map_data` in isolation (tested via `get_map_rotation`)
  - Do NOT merge Pattern A and Pattern B tests (different domains, different contracts)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 9 async functions, 2 error patterns, 4 error types — complex mock orchestration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9-10)
  - **Blocks**: Nothing
  - **Blocked By**: Task 2

  **References**:
  - `nonebot_plugin_apex_api_query/data_source.py:27-70` — `query_apex_api` + `_fetch`
  - `nonebot_plugin_apex_api_query/data_source.py:73-168` — `get_player_stats`
  - `nonebot_plugin_apex_api_query/data_source.py:214-241` — `get_map_rotation_data` (Pattern B)
  - `nonebot_plugin_apex_api_query/data_source.py:243-289` — `get_server_status_data`
  - `nonebot_plugin_apex_api_query/data_source.py:325-346` — `get_predator_data`
  - `nonebot_plugin_apex_api_query/config.py:10-13` — API URL defaults (for mock URL matching)

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_data_source.py -v` → all pass
  - [ ] ≥15 tests total (9 functions × happy + selected error paths)
  - [ ] Pattern A error tests raise ApexAPIError
  - [ ] Pattern B error tests return strings (no exception)
  - [ ] Both API domains mocked: mozambiquehe.re + apexlegendsstatus.com

  **QA Scenarios**:

  ```
  Scenario: data_source API tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_data_source.py -v --tb=short
    Expected Result: ≥15 tests pass, 0 failures
    Evidence: .omo/evidence/task-8-datasource-tests.txt

  Scenario: Both error patterns verified
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_data_source.py -v -k "error or HTTPError or non_200 or JSONDecodeError" --tb=short
    Expected Result: Pattern A raises ApexAPIError, Pattern B returns strings
    Evidence: .omo/evidence/task-8-error-patterns.txt
  ```

  **Commit**: NO

- [x] 9. Write tests/test_storage.py — DB operations with mock session

  **What to do**:
  - Append to `tests/test_storage.py`
  - Use `mock_db_session` fixture from conftest (3-layer async mock chain)
  - Test `save_record()`:
    - Creates PlayerStats with correct fields
    - `session.add()` called once
    - `session.commit()` called once
    - `rank_div` can be None (non-ranked players)
  - Test `get_latest_record()`:
    - Returns PlayerStats when record exists
    - Returns None when no record found
    - Returns most recent by `created_at` (order by DESC)
  - Test `save_record` → `get_latest_record` roundtrip:
    - Save a record, then retrieve it, verify fields match

  **Must NOT do**:
  - Do NOT use real database connection
  - Do NOT test edge cases already covered by format_comparison in Task 7

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 3-layer async mock chain requires precise mock setup; async context manager mocking is error-prone
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: Nothing
  - **Blocked By**: Task 2

  **References**:
  - `nonebot_plugin_apex_api_query/storage.py:19-38` — `get_latest_record`
  - `nonebot_plugin_apex_api_query/storage.py:41-67` — `save_record`
  - Draft: DB Mock Strategy (3-layer chain pattern)

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_storage.py -v -k "save_record or get_latest_record"` → all pass
  - [ ] `save_record` test verifies `session.add()` + `session.commit()`
  - [ ] `get_latest_record` None test passes
  - [ ] Roundtrip test passes (save → retrieve matches)

  **QA Scenarios**:

  ```
  Scenario: DB storage tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_storage.py -v -k "save_record or get_latest_record" --tb=short
    Expected Result: ≥4 tests pass, 0 failures
    Evidence: .omo/evidence/task-9-storage-db.txt
  ```

  **Commit**: NO

- [x] 10. Write tests/test_image.py — render functions

  **What to do**:
  - Append to `tests/test_image.py`
  - Use `reset_image_caches` fixture (autouse from conftest)
  - For `render_map_card`: mock `_download_image` (pre-populate `_image_cache`), pass minimal valid dict with battle_royale/ranked/ltm sections → verify returns non-empty bytes
  - For `render_server_card`: pass minimal list of section dicts → verify returns bytes
  - For `render_predator_card`: pass minimal dict with platform entries → verify returns bytes
  - For `render_player_card`: pass minimal player dict → verify returns bytes
  - Test render functions with edge input: empty dicts, missing keys, None values → verify no crash
  - Test that render output starts with PNG magic bytes (b'\x89PNG')

  **Must NOT do**:
  - Do NOT test pixel correctness or visual appearance
  - Do NOT test `_draw_*` helpers directly (covered by render functions)
  - Do NOT make real HTTP calls (mock `_download_image` or seed cache)
  - Do NOT create reference images

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: PIL canvas manipulation, mock image downloads, font fallback edge cases
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: Nothing
  - **Blocked By**: Task 2

  **References**:
  - `nonebot_plugin_apex_api_query/image.py:336-359` — `render_map_card`
  - `nonebot_plugin_apex_api_query/image.py:413-462` — `render_server_card`
  - `nonebot_plugin_apex_api_query/image.py:517-543` — `render_predator_card`
  - `nonebot_plugin_apex_api_query/image.py:568-706` — `render_player_card`
  - `nonebot_plugin_apex_api_query/image.py:91-93` — Caches to reset

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_image.py -v -k "render"` → all pass
  - [ ] All 4 render functions return non-empty bytes
  - [ ] Render output starts with b'\x89PNG'
  - [ ] Edge case (empty dicts) → no crash

  **QA Scenarios**:

  ```
  Scenario: Image render tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_image.py -v -k "render" --tb=short
    Expected Result: ≥5 tests pass, 0 failures, no assertion errors
    Evidence: .omo/evidence/task-10-image-render.txt

  Scenario: PNG magic bytes verified for all render functions
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_image.py -v -k "png or magic or bytes" --tb=short
    Expected Result: All render functions produce valid PNG output
    Evidence: .omo/evidence/task-10-png-verify.txt
  ```

  **Commit**: YES (Wave 3 batch)
  - Message: `test: add API/DB/image tests`
  - Files: `tests/test_data_source.py`, `tests/test_storage.py`, `tests/test_image.py`

- [x] 11. Write tests/test_handlers.py — apex_player handler (3 paths)

  **What to do**:
  - Append to `tests/test_handlers.py`
  - Use nonebug `app` fixture + `test_matcher` context
  - Test `apex_player` handler 3 critical paths:
    1. **Happy Path**: valid player_name + platform → mock API returns data → mock image returns PNG bytes → verify `MessageSegment.image` in output
    2. **Text-Only Path**: `config.apex_only_text = True` → verify pure text output, no image
    3. **API Error Path**: mock API raises ApexAPIError → verify error text in output
  - Also test:
    - Missing player_name (`None`) → `"请输入玩家名称"`
    - Invalid platform → `"平台参数错误，请输入 PC、PS4、X1、SWITCH"`
    - Image render exception → falls back to text output (no crash)

  **Must NOT do**:
  - Do NOT test DB save/compare logic through handlers (mock `storage.*` entirely)
  - Do NOT test all 12+ handler branches (just the 3 critical + 2 edge)
  - Do NOT import plugin modules at test file level

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: nonebug test_matcher integration, multi-mock orchestration (API + DB + image + config), MessageSegment assertions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 12)
  - **Blocks**: Nothing
  - **Blocked By**: Tasks 2, 8, 9, 10 (all mock fixtures needed)

  **References**:
  - `nonebot_plugin_apex_api_query/__init__.py:60-134` — `apex_player` handler
  - `nonebot_plugin_apex_api_query/data.py:3` — VALID_PLATFORMS for invalid platform test
  - Librarian finding: nonebug test_matcher pattern (from nonebot.dev testing docs)
  - Metis directive: Handler test scope — 3 critical paths per handler

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_handlers.py -v -k "apex_player"` → all pass
  - [ ] Happy path: output contains `MessageSegment.image`
  - [ ] Text-only path: output is pure text, no image
  - [ ] API error path: output contains error message text
  - [ ] Missing name → `"请输入玩家名称"`
  - [ ] Invalid platform → platform error text

  **QA Scenarios**:

  ```
  Scenario: apex_player handler tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_handlers.py -v -k "apex_player" --tb=short
    Expected Result: ≥5 tests pass, 0 failures
    Evidence: .omo/evidence/task-11-handler-player.txt

  Scenario: Text fallback on image render failure
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_handlers.py -v -k "fallback or exception" --tb=short
    Expected Result: Render exception → text output (no crash)
    Evidence: .omo/evidence/task-11-fallback.txt
  ```

  **Commit**: NO

- [x] 12. Write tests/test_handlers.py — apex_map, apex_server, apex_predator

  **What to do**:
  - Append to `tests/test_handlers.py`
  - Test each of the 3 remaining handlers with 3 paths each:
  - `apex_map`:
    1. Happy: mock map data → image bytes → MessageSegment.image
    2. Text-only: `config.apex_only_text=True` → text, no image
    3. API error (string return from `get_map_rotation_data`) → error text
    4. Image render exception → fallback to text
  - `apex_server`:
    1. Happy: mock server data → image bytes
    2. Text-only: text, no image
    3. API error → error text
    4. Image render exception → text fallback
  - `apex_predator`:
    1. Happy: mock predator data → image bytes
    2. Text-only: text, no image
    3. API error → error text
    4. Image render exception → text fallback

  **Must NOT do**:
  - Do NOT duplicate conftest mock setup (reuse existing fixtures)
  - Do NOT test full path coverage

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 3 handlers × 4 paths = 12 test cases, consistent pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 11)
  - **Blocks**: Nothing
  - **Blocked By**: Tasks 2, 8, 9, 10

  **References**:
  - `nonebot_plugin_apex_api_query/__init__.py:170-183` — `apex_map`
  - `nonebot_plugin_apex_api_query/__init__.py:186-199` — `apex_server`
  - `nonebot_plugin_apex_api_query/__init__.py:202-215` — `apex_predator`

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/test_handlers.py -v -k "map or server or predator"` → all pass
  - [ ] ≥10 tests (3 handlers × 3 paths + 1 render exception each)
  - [ ] All happy paths produce image output
  - [ ] All text-only paths produce text
  - [ ] All error paths produce error text
  - [ ] All render exception paths fall back to text

  **QA Scenarios**:

  ```
  Scenario: All handler integration tests pass
    Tool: Bash
    Steps:
      1. poetry run pytest tests/test_handlers.py -v --tb=short
    Expected Result: ≥15 tests pass, 0 failures (11's + 12's tests)
    Evidence: .omo/evidence/task-12-handlers-all.txt
  ```

  **Commit**: YES (Wave 4 batch)
  - Message: `test: add handler integration tests`
  - Files: `tests/test_handlers.py`

- [x] 13. Create .github/workflows/tests.yml

  **What to do**:
  - Create `.github/workflows/tests.yml`
  - Name: Test
  - Triggers: `push` (all branches), `pull_request` (all branches)
  - Strategy matrix: Python `["3.10", "3.11", "3.12"]`
  - Steps:
    1. actions/checkout@v4
    2. actions/setup-python@v5 (with matrix python-version)
    3. Install Poetry: `pipx install poetry`
    4. Install deps: `poetry install --with dev`
    5. Run tests: `poetry run pytest tests/ -v --tb=short`
    6. (Optional) Coverage: `poetry run pytest tests/ --cov=nonebot_plugin_apex_api_query --cov-report=term`
  - Do NOT modify existing `publish.yml`

  **Must NOT do**:
  - Do NOT add test step to publish.yml
  - Do NOT require API keys/secrets for CI tests (all mocked)
  - Do NOT add coverage threshold (add later after baseline)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard GitHub Actions YAML, well-documented pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Task 14)
  - **Blocks**: Nothing
  - **Blocked By**: Tasks 1-12 (tests must exist to run in CI)

  **References**:
  - `.github/workflows/publish.yml` — Existing CI, keep separate
  - `pyproject.toml:15` — `requires-python = ">=3.10,<4.0"` (determines matrix versions)

  **Acceptance Criteria**:
  - [ ] `.github/workflows/tests.yml` exists
  - [ ] Triggers: push + pull_request
  - [ ] Python matrix: 3.10, 3.11, 3.12
  - [ ] Poetry install + pytest run as steps

  **QA Scenarios**:

  ```
  Scenario: CI workflow YAML is valid
    Tool: Bash
    Preconditions: tests.yml created
    Steps:
      1. python -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yml'))"
      2. (if yaml not available) python -c "import json; print('YAML parse check skipped')"
    Expected Result: No parse errors, workflow structure has jobs.test.strategy.matrix.python-version
    Evidence: .omo/evidence/task-13-ci-yaml.txt
  ```

  **Commit**: YES
  - Message: `ci: add test workflow`
  - Files: `.github/workflows/tests.yml`

- [x] 14. Full test suite run + coverage verification

  **What to do**:
  - Run full test suite: `poetry run pytest tests/ -v --tb=short`
  - Run with coverage: `poetry run pytest tests/ --cov=nonebot_plugin_apex_api_query --cov-report=term-missing`
  - Fix any failures, flaky tests, or import errors
  - Verify all 7 modules have test coverage
  - Verify all QA scenarios from Tasks 1-13 pass

  **Must NOT do**:
  - Do NOT skip to this task before Tasks 1-13 complete
  - Do NOT add new tests (fix existing failures only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Execute commands + verify output, no code changes
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Task 13)
  - **Blocks**: Nothing
  - **Blocked By**: Tasks 1-13

  **References**:
  - All test files created in Tasks 3-12

  **Acceptance Criteria**:
  - [ ] `poetry run pytest tests/ -v --tb=short` exits 0, all pass
  - [ ] `poetry run pytest tests/ --cov=nonebot_plugin_apex_api_query --cov-report=term` exits 0
  - [ ] Coverage report shows all 7 source modules
  - [ ] 0 failures, 0 errors, 0 skips

  **QA Scenarios**:

  ```
  Scenario: Full test suite passes
    Tool: Bash
    Steps:
      1. poetry run pytest tests/ -v --tb=short
    Expected Result: ALL tests pass, exit 0, 0 failures
    Evidence: .omo/evidence/task-14-full-suite.txt

  Scenario: Coverage report generated
    Tool: Bash
    Steps:
      1. poetry run pytest tests/ --cov=nonebot_plugin_apex_api_query --cov-report=term
    Expected Result: Exit 0, coverage table visible for all 7 modules
    Evidence: .omo/evidence/task-14-coverage.txt
  ```

  **Commit**: YES (if fixes needed)
  - Message: `test: fix final suite failures`
  - Files: Any test files needing fixes

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. Verify all Must Have present, all Must NOT Have absent. Check evidence files exist in .omo/evidence/.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `poetry run pytest tests/ -v --tb=short`. Review all test files for: flaky tests (time-dependent), test isolation violations, missing assertions, over-mocking.
  Output: `Tests [N pass/N fail] | Quality [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Execute every QA scenario from every task. Test cross-task integration: run full suite, verify CI workflow YAML structure.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- **1-7**: `test: add test infrastructure foundation` — conftest.py + pyproject.toml + pure function tests
- **8-10**: `test: add API/DB/image tests` — data_source + storage + image render
- **11-12**: `test: add handler integration tests` — nonebug command flow
- **13-14**: `ci: add test workflow` — CI + final suite run

---

## Success Criteria

### Verification Commands
```bash
poetry run pytest tests/ -v                          # Expected: ALL PASS, 0 failures
poetry run pytest tests/ --cov=nonebot_plugin_apex_api_query --cov-report=term  # Expected: coverage report
```

### Final Checklist
- [ ] All 7 source modules have corresponding test files
- [ ] `poetry run pytest tests/ -v` exits 0
- [ ] `.github/workflows/tests.yml` passes CI
- [ ] All "Must NOT Have" items absent
- [ ] No module-level plugin imports in test files
