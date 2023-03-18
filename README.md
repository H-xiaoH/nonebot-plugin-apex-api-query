<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-apex-api-query

_✨ 基于 NoneBot 的 Apex Legends API 查询插件 ✨_


<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/H-xiaoH/nonebot-plugin-apex-api-query.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-apex-api-query">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-apex-api-query.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">

</div>

## 📖 介绍

基于 NoneBot2 且使用 OneBot V11 协议 的 [Apex Legends API](https://apexlegendsstatus.com/) 查询插件。

您可以在 [此处](https://portal.apexlegendsapi.com/) 申请您自己的 API 密钥。
申请密钥后重新在 [此页面](https://portal.apexlegendsapi.com/) 登录 API 密钥以测试密钥是否可用。
必须将此 API 密钥 [链接](https://portal.apexlegendsapi.com/discord-auth) 至您的 Discord 账户后您的 API 密钥才可用。

由于 API 的问题，您只能在查询玩家信息时使用 EA 账户用户名并非 Steam 账户用户名。

## 💿 安装

<details>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot_plugin_apex_api_query

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot_plugin_apex_api_query
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot_plugin_apex_api_query
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_apex_api_query"]

</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| APEX_API_KEY | 是 | None | API 密钥 |
| APEX_API_URL | 否 | https://api.mozambiquehe.re/ | API 链接地址 |
| APEX_API_T2I | 否 | True | 文字转图片 |

## 🎉 使用
### 指令表
| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| 玩家 [玩家名称] | 无 | 否 | 私聊/群聊/频道 | 根据玩家名称查询信息 (暂仅支持查询 PC 平台玩家信息) |
| UID [玩家UID] | 无 | 否 | 私聊/群聊/频道 | 根据玩家 UID 查询信息 (暂仅支持查询 PC 平台玩家信息) |
| 自查 | 无 | 否 | 私聊/群聊/频道 | 根据玩家已绑定的 UID 自动查询玩家信息 |
| 地图 | 无 | 否 | 私聊/群聊/频道 | 查询地图轮换 |
| 猎杀 | 无 | 否 | 私聊/群聊/频道 | 查询各平台顶尖猎杀者信息 |
| 制造 | 无 | 否 | 私聊/群聊/频道 | 查询复制器轮换 |
| 服务 | 无 | 否 | 私聊/群聊/频道 | 查询服务器状态 |
| 订阅地图 | 管理员 | 否 | 群聊/频道 | 每整点查询地图轮换 |
| 取消订阅地图 | 管理员 | 否 | 群聊/频道 | 取消每整点查询地图轮换 |
| 订阅制造 | 管理员 | 否 | 群聊/频道 | 每日 2 时查询复制器轮换 |
| 取消订阅制造 | 管理员 | 否 | 群聊/频道 | 取消每日 2 时查询复制器轮换 |
| 绑定 [玩家 UID] | 无 | 否 | 私聊/群聊/频道 | 将 UID 与 QQ 账号绑定 (群聊 与 频道 信息不互通) |
| 解绑 | 无 | 否 | 私聊/群聊/频道 | 将 UID 与 QQ 账号解除绑定 (群聊 与 频道 信息不互通) |

## 📄 ToDo

如您有想要的功能，请提交 [Issues](https://github.com/H-xiaoH/nonebot-plugin-apex-api-query/issues) 。

## 🌸 致谢

- [@nonebot](https://github.com/nonebot) 强大的 [NoneBot2 机器人框架](https://github.com/nonebot/nonebot2)

- [@nonebot](https://github.com/nonebot) 订阅功能基于 [APScheduler 定时任务插件](https://github.com/nonebot/plugin-apscheduler)

- [@nonebot](https://github.com/nonebot) 本地数据存储功能基于 [本地数据存储](https://github.com/nonebot/plugin-localstore)

- [@A-kirami](https://github.com/A-kirami) 使用其 NoneBot Plugin [README 模板](https://github.com/A-kirami/nonebot-plugin-template)

- [@mobyw](https://github.com/mobyw) 文字转图片功能源于 [轻量文字转图片插件](https://github.com/mobyw/nonebot-plugin-txt2img)
