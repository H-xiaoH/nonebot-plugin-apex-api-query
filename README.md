<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# nonebot-plugin-apex-api-query

*✨ NoneBot Apex Legends API 查询插件 ✨*

![GitHub](https://img.shields.io/github/license/H-xiaoH/nonebot-plugin-apex-api-query)
![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-apex-api-query)

</div>

## 使用方法

在您的 NoneBot 配置文件中写入 `APEX_API_KEY` 值。

您可以在 [NoneBot2 官方文档](https://v2.nonebot.dev/docs/tutorial/configuration) 中获取配置方法。

例如:
```text
HOST=127.0.0.1
PORT=8080
LOG_LEVEL=DEBUG
FASTAPI_RELOAD=true
NICKNAME=["Bot"]
COMMAND_START=["/", ""]
COMMAND_SEP=["."]
APEX_API_KEY=173fd0ee53fb32d4c7063eb5bc700c9e
```

## Application Programming Interface

您可以在 [此处](https://portal.apexlegendsapi.com/) 申请您自己的 API 密钥。

首次创建 API 密钥时，每两秒只能发出一个请求。通过与您的 Discord 帐户连接，此限制可以增加到每一秒发出两个请求。为此，请单击 [此处](https://portal.apexlegendsapi.com/) 登录您的 API 并链接您的 Discord 账户以增加请求频率。

由于 API 的问题，您只能在查询玩家信息时使用 EA 账户用户名并非 Steam 账户用户名。

### 查询玩家信息

`/bridge [玩家名称]` 、
`/玩家 [玩家名称]`

`/uid [玩家UID]`、
`/UID [玩家UID]`

暂不支持除 PC 以外的平台查询。

输出示例：
```text
玩家信息:
名称: HxiaoH
UID: 1002727553409
平台: PC
等级: 256
距下一级百分比: 86%
封禁状态: 否
剩余秒数: 0
最后封禁原因: 竞技逃跑冷却
大逃杀分数: 10418
大逃杀段位: 白金 2
竞技场分数: 2317
竞技场段位: 白银 3
大厅状态: 打开
在线: 是
游戏中: 是
可加入: 是
群满员: 否
已选传奇: 寻血猎犬
当前状态: 比赛中
```

### 查询大逃杀地图轮换

`/maprotation` 、 `/地图`

输出示例：
```text
大逃杀:
当前地图: 世界尽头
下个地图: 破碎月亮
剩余时间: 00:43:15

竞技场:
当前地图: 相位穿梭器
下个地图: 栖息地 4
剩余时间: 00:13:15

排位赛联盟:
当前地图: 破碎月亮
下个地图: 奥林匹斯
剩余时间: 599:43:15

排位竞技场:
当前地图: 相位穿梭器
下个地图: 栖息地 4
剩余时间: 00:13:15
```

### 查询猎杀者信息

`/predator` 、 `/猎杀`

输出示例：
```text
大逃杀:
PC 端:
顶尖猎杀者人数: 750
顶尖猎杀者分数: 34176
顶尖猎杀者UID: 1008992986436
大师和顶尖猎杀者人数: 20995
PS4/5 端:
顶尖猎杀者人数: 752
顶尖猎杀者分数: 25039
顶尖猎杀者UID: 6655163505495496802
大师和顶尖猎杀者人数: 7382
Xbox 端:
顶尖猎杀者人数: 750
顶尖猎杀者分数: 20262
顶尖猎杀者UID: 2535442891191517
大师和顶尖猎杀者人数: 2947
Switch 端:
顶尖猎杀者人数: -1
顶尖猎杀者分数: 15000
顶尖猎杀者UID: -1
大师和顶尖猎杀者人数: 671

竞技场:
PC 端:
顶尖猎杀者人数: 750
顶尖猎杀者分数: 9735
顶尖猎杀者UID: 1010770350454
大师和顶尖猎杀者人数: 2919
PS4/5 端:
顶尖猎杀者人数: 749
顶尖猎杀者分数: 10279
顶尖猎杀者UID: 5266195274595015901
大师和顶尖猎杀者人数: 5226
Xbox 端:
顶尖猎杀者人数: 751
顶尖猎杀者分数: 8578
顶尖猎杀者UID: 2535421772058188
大师和顶尖猎杀者人数: 1821
Switch 端:
顶尖猎杀者人数: -1
顶尖猎杀者分数: 8000
顶尖猎杀者UID: -1
大师和顶尖猎杀者人数: 291
```

### 查询复制器轮换

`/crafting` 、 `/制造`

输出示例：
```text
每日制造:
4 倍至 8 倍可调节式狙击手 等级3 35 点
加长狙击弹匣 等级3 35 点

每周制造:
击倒护盾 等级3 30 点
移动重生信标 等级2 50 点

赛季制造:
和平捍卫者 等级1 30 点
喷火轻机枪 等级1 30 点
```

### 订阅制造/地图轮换

`/submap`、`/订阅地图`

`/unsubmap`、`/取消订阅地图`

订阅地图轮换时将每小时自动查询地图轮换并推送。

`/subcraft`、`/订阅制造`

`/unsubcraft`、`/取消订阅制造`

订阅制造轮换时将每日 2 时时自动查询制造轮换并推送。


