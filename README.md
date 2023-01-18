<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# nonebot-plugin-apex-api-query

*✨ NoneBot Apex Legends API 查询插件 ✨*

![GitHub](https://img.shields.io/github/license/H-xiaoH/nonebot-plugin-apex-api-query)
![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-apex-api-query)

</div>

## 配置项

您可以在 [NoneBot2 官方文档](https://v2.nonebot.dev/docs/tutorial/configuration) 中查看配置文件的配置方法。

例如:
```text
HOST=127.0.0.1
PORT=8080
LOG_LEVEL=DEBUG
FASTAPI_RELOAD=true
NICKNAME=["Bot"]
COMMAND_START=["/", ""]
COMMAND_SEP=["."]
APEX_API_KEY='173fd0ee53fb32d4c7063eb5bc700c9e'
```

### APEX_API_KEY

您的 32 位 API 密钥。

`APEX_API_KEY='173fd0ee53fb32d4c7063eb5bc700c9e'`

### APEX_API_T2I

文字转图片发送内容

- `True` = 开启 (默认)
- `False` = 关闭

## Application Programming Interface

您可以在 [此处](https://portal.apexlegendsapi.com/) 申请您自己的 API 密钥。
申请密钥后重新在 [此页面](https://portal.apexlegendsapi.com/) 登录 API 密钥以测试密钥是否可用。
必须将此 API 密钥 [链接](https://portal.apexlegendsapi.com/discord-auth) 至您的 Discord 账户后您的 API 密钥才可用。

由于 API 的问题，您只能在查询玩家信息时使用 EA 账户用户名并非 Steam 账户用户名。

## 使用方式

`/bridge [玩家名称]` 、`/玩家 [玩家名称]` - 根据玩家名称查询玩家信息 (暂仅支持查询 PC 平台玩家信息)

`/uid [玩家UID]`、`/UID [玩家UID]` - 根据玩家 UID 查询玩家信息 (暂仅支持查询 PC 平台玩家信息)

`/maprotation` 、 `/地图` - 查询当前地图轮换

`/predator` 、 `/猎杀` - 查询顶尖猎杀者信息

`/crafting` 、 `/制造` - 查询当前制造轮换

`/servers`、`/服务` - 查看当前服务器状态

`/submap`、`/订阅地图` - 订阅地图轮换(每整点查询)(仅群聊可用)

`/unsubmap`、`/取消订阅地图` - 取消订阅地图轮换(仅群聊可用)

`/subcraft`、`/订阅制造` - 订阅制造轮换(每日2时查询)(仅群聊可用)

`/unsubcraft`、`/取消订阅制造` - 取消订阅制造轮换(仅群聊可用)

