# AGENTS.md — nonebot-plugin-apex-api-query

本仓库 OpenCode 会话的快速入门指南。这是一个 3 文件 + JSON 翻译的 NoneBot2 插件，通过单一 API 主机查询 Apex Legends 数据并渲染图片卡片。

## 快速开始
```bash
poetry install
# 插件仅在运行中的 NoneBot2 机器人内加载。
```

## 架构
单包 NoneBot2 插件，3 个 .py 文件 + JSON 翻译 + 字体目录。

| 文件 | 用途 |
|---|---|
| `__init__.py` | 插件入口：Alconna 命令、4 个处理器、API 客户端（httpx）、数据获取、图片渲染（PIL+numpy）、缓存（AsyncTTLCache）、数据库读写、历史数据对比（约 1400 行单体文件） |
| `config.py` | Pydantic `Config` 模型 — `get_plugin_config(Config)` 调用，`field_validator` 校验 API 密钥 |
| `models.py` | SQLAlchemy ORM 模型 `PlayerStats` (`apex_player_stats`)，索引 `idx_uid_platform`，`rank_div` 可为空 |
| `data/translations.json` | JSON 翻译字典（替代原 `data.py`），游戏内容中文翻译，通过 `convert()` 函数首次调用时懒加载 |
| `fonts/` | `NotoSansSC-VariableFont_wght.ttf`（可变字重） |

入口点：`apex_api_query = "nonebot_plugin_apex_api_query"` (pyproject.toml:29)

## API 端点
| 配置键 | 默认值 | 用途 |
|---|---|---|
| `apex_api_url` | `https://api.apexlegendsstatus.com` | 所有查询（玩家/地图/服务器/顶猎）共享此单一主机 |

`_fetch()` 函数处理所有 API 调用，使用统一的错误处理模式：网络错误、非 200 状态码、JSON 解析失败均抛出 `ApexAPIError`。

## 必须配置
`APEX_API_KEY` 在**插件加载时必须提供**。`Config` 模型的 `field_validator` 在为空时抛出 `MissingAPIKeyError` — 插件将无法加载。
```env
APEX_API_KEY = "your-key"
APEX_API_URL = "https://api.apexlegendsstatus.com"
APEX_ONLY_TEXT = False    # 设为 True 跳过图片渲染
```

## 命令流程
使用 `nonebot_plugin_alconna`（`Alconna(["/", "."], "apex", ...)` + `on_alconna`）。支持 `/apex` 和 `.apex` 前缀，通过 `dispatch` 分发子命令：
- `$main` → 玩家数据（需要玩家名称参数）
- `map` / `m` / `地图` → 地图轮换
- `server` / `s` / `服务器` → 服务器状态
- `predator` / `p` / `顶猎` → 顶猎排行

`ErrorLogExtension` 处理未解析的依赖名称，记录警告并返回默认值。

**统一回退模式（map/server/predator 处理器使用 `_render_or_fallback()`）：**
1. 检查 `config.apex_only_text` → 若为 True 则跳过渲染
2. 获取结构化数据（含文本）
3. 数据为空 → 直接返回文本
4. 尝试 PIL 渲染 → `asyncio.to_thread(_run_async, render_fn, data)`
5. 出现异常 → 记录警告，回退到纯文本输出

**玩家处理器例外：** `apex_player` 有自己内联的 `apex_only_text` 检查和渲染逻辑（不使用 `_render_or_fallback`），因为在渲染前需要先进行历史数据对比和保存。

所有处理器通过 `UniMessage.image(raw=pic_bytes)` 发送图片（适配器无关，非 OneBot 专用）。

## 数据库
使用 `nonebot_plugin_orm`（SQLAlchemy 异步）。表 `apex_player_stats` 在启动时自动创建。`os.environ.setdefault("ALEMBIC_STARTUP_CHECK", "false")` 禁用 Alembic 迁移检查。索引：`idx_uid_platform` 基于 `(uid, platform)`。`rank_div` 字段可为空（`int | None`）。

`get_session()` 上下文管理器用于所有数据库读写。玩家数据通过 `get_latest_record()` 查询历史记录，`save_record()` 持久化新记录，`format_comparison()` 对比当前与上一次数据生成变化标记。

## 图片渲染
- 字体：`Path(__file__).parent / "fonts" / "NotoSansSC-VariableFont_wght.ttf"` — 通过 `font.setvaraxes([weight])` 支持可变字重。字体缺失时回退到 PIL 默认字体。
- 字体缓存：`_font_cache` 字典，按 `(size, weight)` 键缓存。
- 地图图片通过 `get_plugin_data_dir() / "map_images"` 缓存到磁盘（重启后持久保留），同时维护内存 `_image_cache` 字典。
- 使用 PIL + numpy（用于地图卡片渐变叠加）。
- **所有 4 种卡片类型均通过 `_draw_footer()` 绘制 "Data from apexlegendsstatus.com" 脚注**：`render_player_card`、`render_map_card`、`render_server_card`、`render_predator_card`。

## 翻译
游戏内容翻译以 JSON 字典形式存放在 `data/translations.json` 中（166 行）。`convert()` 函数在首次调用时懒加载该 JSON 文件（通过 `hasattr` 检查），无对应翻译时返回原始键名。无外部国际化框架。添加翻译只需编辑 JSON 文件追加条目。

## 缓存
`AsyncTTLCache` 类 — 基于 TTL 的异步缓存，使用 `asyncio.Lock` 保证并发安全。过期条目在下次访问时自动清除。

三个实例，不同 TTL：
- `get_map_rotation_data._cache` — 60 秒
- `get_server_status_data._cache` — 30 秒
- `get_predator_data._cache` — 300 秒（5 分钟）

缓存数据命中时立即返回，无需发起 API 请求。

## CI / 发布
推送到 `main` 分支 → Poetry 构建 → 发布到 PyPI（OIDC 可信发布，`pypa/gh-action-pypi-publish@release/v1`）。无需 API 令牌。版本约定：`26.6.14`（基于日期）。`tests.yml` 在 push/PR 时运行。

**版本管理规则：** 每次推送前必须将 `pyproject.toml` 中的 `version` 字段更新为当天日期（格式 `YY.M.D`，如 `26.6.22`），确保 PyPI 发布时版本号唯一且语义化。
