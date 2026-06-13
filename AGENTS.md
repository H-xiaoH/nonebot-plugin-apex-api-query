# AGENTS.md — nonebot-plugin-apex-api-query

本仓库 OpenCode 会话的快速入门指南。这是一个 8 文件的 NoneBot2 插件，通过两个 API 主机查询 Apex Legends 数据并渲染图片卡片。

## 快速开始
```bash
poetry install
# 无测试配置。无 lint/typecheck 配置。
# 插件仅在运行中的 NoneBot2 机器人内加载。
```

## 架构
单包 NoneBot2 插件，扁平 8 文件 + 字体目录。

| 文件 | 用途 |
|---|---|
| `__init__.py` | 插件入口：Alconna 命令、4 个处理器、数据库自动创建 |
| `config.py` | Pydantic `Config` 模型 — 加载时必须提供 `APEX_API_KEY` |
| `data_source.py` | HTTP API 客户端 (httpx) — 两个端点，错误处理 |
| `data.py` | 静态翻译字典 + 常量 |
| `models.py` | SQLAlchemy ORM 模型 `PlayerStats` (`apex_player_stats`) |
| `storage.py` | 数据库读写，保存玩家记录，对比当前与上一次数据 |
| `image.py` | PIL+numpy 图片渲染（4 种卡片类型：player/map/server/predator） |
| `fonts/` | `NotoSansSC-VariableFont_wght.ttf` |

入口点：`apex_api_query = "nonebot_plugin_apex_api_query"` (pyproject.toml:28-29)

## 两个 API 端点（重要）
| 配置键 | 默认值 | 用途 |
|---|---|---|
| `APEX_API_URL` | `https://api.mozambiquehe.re` | 玩家数据、服务器状态、顶猎排行 |
| `APEX_MAP_API_URL` | `https://api.apexlegendsstatus.com` | 仅地图轮换 |

地图轮换使用**不同的域名**，在 `data_source.py` 中有独立的请求和错误处理。不要混用两个端点。

## 必须配置
`APEX_API_KEY` 在**插件加载时必须提供**。`Config` 模型的 `field_validator` 在为空时抛出 `MissingAPIKeyError` — 插件将无法加载。
```env
APEX_API_KEY = "your-key"
APEX_ONLY_TEXT = False    # 设为 True 跳过图片渲染
```

## 命令流程
使用 `nonebot_plugin_alconna`（`Alconna` + `on_alconna`）。主命令 `/apex`：
- `$main` → 玩家数据（需要玩家名称参数）
- `map` / `m` / `地图` → 地图轮换
- `server` / `s` / `服务器` → 服务器状态
- `predator` / `p` / `顶猎` → 顶猎排行

**每个图片处理器遵循相同的回退模式：**
1. 检查 `config.apex_only_text` → 若为 True 则跳过渲染
2. 从 data_source 获取结构化数据
3. 尝试 PIL 渲染（`image.render_*_card()`）
4. 出现异常 → 记录警告，回退到纯文本输出

## 数据库
使用 `nonebot_plugin_orm`（SQLAlchemy 异步）。表 `apex_player_stats` 在启动时通过 `@driver.on_startup` 自动创建 — 无需迁移。索引：`(uid, platform)`。

## 图片渲染
- 字体：`Path(__file__).parent / "fonts" / "NotoSansSC-VariableFont_wght.ttf"` — 通过 `font.setvaraxes([weight])` 支持可变字重。字体缺失时回退到 PIL 默认字体。
- 地图图片通过 `nonebot_plugin_localstore` 缓存（`get_plugin_data_dir() / "map_images"`），重启后持久保留。
- 使用 PIL + numpy（用于渐变叠加）。

## 翻译
所有游戏内容翻译以字典映射形式存放在 `data.py` 中。`convert()` 在无对应翻译时返回原始键名。无外部国际化框架。在 `data.py` 的字典中追加条目即可添加翻译。

## CI / 发布
推送到 `main` 分支 → Poetry 构建 → 发布到 PyPI（OIDC 可信发布，`pypa/gh-action-pypi-publish@release/v1`）。无需 API 令牌。版本约定：`26.5.28`（基于日期）。

## 无测试基础设施
无测试文件，无测试框架，无 CI 测试步骤。`.gitignore` 包含 pytest/coverage 模式但未被使用。添加测试时需从头搭建。
