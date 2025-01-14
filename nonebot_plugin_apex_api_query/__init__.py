from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, Option, on_alconna, CommandMeta
from .config import Config
from . import data_source as ds


# 插件元数据
__plugin_meta__ = PluginMetadata(
    name="Apex API Query",
    description="Apex Legends API 查询插件",
    usage="/apex",
    type="application",
    homepage="https://github.com/H-xiaoH/nonebot-plugin-apex-api-query",
    config=Config,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna"
        ),
    extra = {
        "author": "H-xiaoH <a412454922@gmail.com>"
        }
)

# 注册命令
apex = on_alconna(
    Alconna(
        "apex",
        Args["player_name?#玩家名称", str]["platform?#平台", str],
        Option("m|map|地图", dest = "map", help_text="查询地图信息"),
        Option("s|server|服务器", dest = "server", help_text="查询服务器状态"),
        Option("p|predator|顶猎", dest = "predator", help_text="查询顶猎分数"),
        meta = CommandMeta(
            description = __plugin_meta__.description,
            usage = __plugin_meta__.usage,
            example = "/apex [玩家名称/地图/服务器/顶猎] [平台]",
            author = __plugin_meta__.extra["author"]
        )
    )
)

# 注册命令处理函数
@apex.assign("$main")
async def apex_player(player_name: str | None = None, platform: str = "PC"):
    if player_name is None:
        await apex.finish("请输入玩家名称")
    elif platform not in ["PC", "PS4", "X1", "Switch"]:
        await apex.finish("平台参数错误，请输入 PC、PS4、X1 或 Switch")
    msg = await apex.finish(str(await ds.get_player_stats(player_name, platform)))
    await apex.finish(msg)

# 处理地图轮换
@apex.assign("map")
async def apex_map():
    msg = await apex.finish(str(await ds.get_map_rotation()))
    await apex.finish(msg)

# 处理服务器状态
@apex.assign("server")
async def apex_server():
    msg = await apex.finish(str(await ds.get_server_status()))
    await apex.finish(msg)

# 处理猎杀者信息
@apex.assign("predator")
async def apex_predator():
    msg = await apex.finish(str(await ds.get_predator()))
    await apex.finish(msg)
