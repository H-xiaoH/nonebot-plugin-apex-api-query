# AGENTS.md — nonebot-plugin-apex-api-query

默认用中文回复；代码标识、命令和日志保留原文。

## 开发与验证

```bash
poetry install --with dev
poetry run python -m unittest discover -s tests -v
```

插件需要在初始化后的 NoneBot 中加载。真实平台连接、API 密钥和 htmlrender 配置见 README.md 的配置章节；测试使用隔离配置，不读取本机机器人的密钥。

## 代码入口

- `nonebot_plugin_apex_api_query/__init__.py`：Alconna 命令、API 数据校验、缓存、历史对比和异步卡片渲染。
- `config.py`：Pydantic 配置。省略、空字符串和纯空白 `APEX_API_KEY` 都允许加载；启动时异步检查可用性，认证失败只记录脱敏日志，聊天命令回复“API密钥不可用”。网络故障、限流和服务端错误不得误判为密钥无效。
- `models.py`：历史表 `PlayerStats` 和绑定表 `PlayerBinding`；历史的 `rank_div`、`prestige` 可空。
- `bindings.py`：按聊天用户读写绑定；适配器、底层平台、机器人 ID 组成命名空间，群聊和私聊共享。
- `templates/`：htmlrender + Playwright 使用的五个 HTML 模板；字体在 `fonts/`，翻译在 `data/translations.json`。

## 查询与消息

`/apex` 和 `.apex` 支持玩家、map/m/地图、server/s/服务器、predator/p/顶猎。API 查询共享配置的单一主机。

`bind/绑定 <名称> [平台]`、`binduid/绑定UID <UID> [平台]` 验证后保存一个账号；`bind/绑定` 查看，`unbind/解绑` 删除绑定。无参数 `/apex` 查询自己的绑定；绑定按 UID 查询，纯数字名称仍按名称处理。API 失败不得覆盖现有绑定。

- `_fetch()` 将网络错误、非 200、无效 JSON 和非对象响应转成 `ApexAPIError`。
- 玩家必需的 UID、等级、段位和分数先校验，再生成输出及保存历史；缺失值不能当作真实零值。
- `APEX_ONLY_TEXT=True` 跳过渲染。渲染、严格图片导出或发送失败时返回完整文字。
- 图片通过 `UniMessage` 发送，禁止静默退化为 `[image]` 占位符。适配器由机器人安装、注册，OneBot 仅为开发依赖。

## 历史与缓存

- 使用 ORM 异步会话读写。默认关闭 Alembic 检查，沿用 ORM 启动时自动同步模式。
- ORM 的 SQLite extra 是运行依赖；默认使用 localstore 管理的 ORM 数据库，保持用户自定义数据库配置和旧历史记录。
- 修改模型后验证旧表迁移并保留旧记录；本机数据库变更前备份。
- 等级比较使用 `prestige * 500 + level`。旧记录没有转生层级时跳过等级对比，分数和段位仍可比较。
- 单进程内按 UID、平台串行读取、比较、保存历史，以查询开始时间拒绝迟到旧结果写入或比较；多进程共享数据库需另行提供跨进程保护。
- 地图、服务器和顶猎分别缓存 60、30、300 秒；同一端点的并发缓存未命中合并为一次请求，失败结果不缓存。
- 图片持久化在 `get_plugin_data_dir()/card_images`，键为 URL 的 SHA-256；404/410 缓存一小时。
- 可选图片每张总下载预算 10 秒、上限 8 MiB；失败时使用背景或默认头像回退。

## 测试与发布

- `tests/bootstrap.py` 加载真实插件；`tests/runtime_check.py` 在独立进程验证旧 SQLite 表迁移、ORM 历史、并发和 Console 命令。
- 浏览器及真实 API 的验证属于额外集成检查；无网络的测试套件不启动浏览器。
- `.github/workflows/publish.yml` 在 PR 和 main 推送运行 Python 3.10、3.12 测试；仅 main 推送且测试全部通过才构建并通过 OIDC 发布 PyPI。

**版本管理规则：** 每次推送前必须将 `pyproject.toml` 中的 `version` 字段更新为当天日期（格式 `YY.M.D`，如 `26.6.22`），确保 PyPI 发布时版本号唯一且语义化。

**Commit 格式规则：** 使用 `emoji type: 中文描述` 格式，emoji 和 type 之间加空格。例如：
- `📌 bump: 版本号更新至 26.6.22`
- `♻️ refactor: 重构代码结构，移除 numpy 依赖`
- `📝 docs: 添加版本管理规则`
- `🌐 i18n: 添加离线和大厅状态翻译`
- `🔥 chore: 移除 CI 测试工作流`

type 对应关系：`bump`（版本更新）、`refactor`（重构）、`feat`（新功能）、`fix`（修复）、`docs`（文档）、`chore`（杂项）、`i18n`（国际化）等。
