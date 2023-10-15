from nonebot import get_driver, require, on_command
from nonebot.adapters import Bot, Message
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.params import CommandArg
from httpx import AsyncClient
from .config import Config

require("nonebot_plugin_saa")

from nonebot_plugin_saa import MessageFactory

__plugin_meta = PluginMetadata(
    name="Apex API Query",
    description="Apex Legends API 查询插件",
    usage="\
        /玩家 [玩家名称] - 根据提供的玩家名称查询玩家信息 (暂仅支持 PC 平台玩家),\n\
        /地图 - 查询当前地图轮换信息,\n\
        /制造 - 查询当前制造轮换信息\
        ",
    config=Config,
    homepage="https://github.com/H-xiaoH/nonebot-plugin-apex-api-query",
    type="application",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_saa")
)

global_config = get_driver().config
config = Config.parse_obj(global_config)
api_key = config.apex_api_key
api_url = config.apex_api_url

player = on_command("玩家")
map = on_command("地图")
crafting = on_command("制造")

@player.handle()
async def _(bot: Bot, player_name: Message = CommandArg()):
    if not player_name:
        await MessageFactory("用法: /玩家 [玩家名称]").send(reply=True)
        await player.finish()
    data = await api_query.player(player_name)
    await MessageFactory(data).send(reply=True)
    await player.finish()

@map.handle()
async def _(bot: Bot):
    data = await api_query.map()
    await MessageFactory(data).send(reply=True)
    await map.finish()

@crafting.handle()
async def _(bot: Bot):
    data = await api_query.crafting()
    await MessageFactory(data).send(reply=True)
    await crafting.finish()

class api_query:

    async def query(service, payload):
        async with AsyncClient() as client:
            response = await client.get(api_url + service, params = payload, timeout = None)
        return response
    
    async def player(player_name):
        service = 'bridge'
        payload = {'auth': api_key, 'player': str(player_name), 'platform': 'PC'}
        response = await api_query.query(service, payload)
        globals = response.json().get('global')
        realtime = response.json().get('realtime')
        data = (
            '玩家信息:\n'
            '名称: {}\n'
            'UID: {}\n'
            '平台: {}\n'
            '等级: {}\n'
            '大逃杀分数: {}\n'
            '大逃杀段位: {} {}\n'
            '大厅状态: {}\n'
            '在线: {}\n'
            '游戏中: {}\n'
            '可加入: {}\n'
            '群满员: {}\n'
            '已选传奇: {}\n'
            '当前状态: {}'
            .format(
                globals.get('name'),
                globals.get('uid'),
                globals.get('platform'),
                globals.get('level'),
                globals.get('rank').get('rankScore'),
                convert(globals.get('rank').get('rankName')),
                globals.get('rank').get('rankDiv'),
                convert(realtime.get('lobbyState')),
                convert(realtime.get('isOnline')),
                convert(realtime.get('isInGame')),
                convert(realtime.get('canJoin')),
                convert(realtime.get('partyFull')),
                convert(realtime.get('selectedLegend')),
                convert(realtime.get('currentState'))
            )
        )
        return data

    async def map():
        service = 'maprotation'
        payload = {'auth': api_key, 'version': '2'}
        response = await api_query.query(service, payload)
        battle_royale = response.json().get('battle_royale')
        ranked = response.json().get('ranked')
        ltm = response.json().get('ltm')
        data = (
            '大逃杀:\n'
            '当前地图: {}\n'
            '下个地图: {}\n'
            '剩余时间: {}\n\n'
            '排位赛联盟:\n'
            '当前地图: {}\n'
            '下个地图: {}\n'
            '剩余时间: {}\n\n'
            '混合模式:\n'
            '当前地图: {}\n'
            '下个地图: {}\n'
            '剩余时间: {}'
            .format(
                convert(battle_royale.get('current').get('map')),
                convert(battle_royale.get('next').get('map')),
                convert(battle_royale.get('current').get('remainingTimer')),
                convert(ranked.get('current').get('map')),
                convert(ranked.get('next').get('map')),
                convert(ranked.get('current').get('remainingTimer')),
                convert(ltm.get('current').get('map')),
                convert(ltm.get('next').get('map')),
                convert(ltm.get('current').get('remainingTimer'))
            )
        )
        return data
    
    async def crafting():
        service = 'crafting'
        payload = {'auth': api_key}
        response = await api_query.query(service, payload)
        data = (
            '每日制造:\n'
            '{} {} {} 点\n'
            '{} {} {} 点\n\n'
            '每周制造:\n'
            '{} {} {} 点\n'
            '{} {} {} 点\n\n'
            '赛季制造:\n'
            '{} {} {} 点\n'
            '{} {} {} 点'
            .format(
                convert(response.json()[0]['bundleContent'][0]['itemType']['name']),
                convert(response.json()[0]['bundleContent'][0]['itemType']['rarity']),
                convert(response.json()[0]['bundleContent'][0]['cost']),
                convert(response.json()[0]['bundleContent'][1]['itemType']['name']),
                convert(response.json()[0]['bundleContent'][1]['itemType']['rarity']),
                convert(response.json()[0]['bundleContent'][1]['cost']),
                convert(response.json()[1]['bundleContent'][0]['itemType']['name']),
                convert(response.json()[1]['bundleContent'][0]['itemType']['rarity']),
                convert(response.json()[1]['bundleContent'][0]['cost']),
                convert(response.json()[1]['bundleContent'][1]['itemType']['name']),
                convert(response.json()[1]['bundleContent'][1]['itemType']['rarity']),
                convert(response.json()[1]['bundleContent'][1]['cost']),
                convert(response.json()[2]['bundleContent'][0]['itemType']['name']),
                convert(response.json()[2]['bundleContent'][0]['itemType']['rarity']),
                convert(response.json()[2]['bundleContent'][0]['cost']),
                convert(response.json()[3]['bundleContent'][0]['itemType']['name']),
                convert(response.json()[3]['bundleContent'][0]['itemType']['rarity']),
                convert(response.json()[3]['bundleContent'][0]['cost'])
            )
        )
        return data

def convert(name):
    names = {
        # Map
        'Kings Canyon': '诸王峡谷',
        'World\'s Edge': '世界尽头',
        'Olympus': '奥林匹斯',
        'Storm Point': '风暴点',
        'Broken Moon': '残月',
        'Encore': '再来一次',
        'Habitat': '栖息地 4',
        'Overflow': '熔岩流',
        'Phase runner': '相位穿梭器',
        'Party crasher': '派对破坏者',
        'Drop Off': '原料场',
        'Skulltown': '骷髅镇',
        'Barometer': '气压计',
        'Wall': '高墙',
        'Siphon': '岩浆汲取器',
        'Fragment': '碎片东部',
        'Unknown': '未知',
        'None': '无',
        # Barrels
        'barrel_stabilizer': '枪管稳定器',
        'laser_sight': '激光瞄准镜',
        # Mags
        'extended_energy_mag': '加长式能量弹匣',
        'extended_heavy_mag': '加长式重型弹匣',
        'extended_light_mag': '加长式轻型弹匣',
        'extended_sniper_mag': '加长狙击弹匣',
        'shotgun_bolt': '霰弹枪枪栓',
        # Optics
        'optic_hcog_classic': '单倍全息衍射式瞄准镜"经典"',
        'optic_holo': '单倍幻影',
        'optic_variable_holo': '单倍至 2 倍可调节式幻影瞄准镜',
        'optic_hcog_bruiser': '2 倍全息衍射式瞄准镜"格斗家"',
        'optic_sniper': '6 倍狙击手',
        'optic_variable_aog': '2 倍至 4 倍可调节式高级光学瞄准镜',
        'optic_hcog_ranger': '3 倍全息衍射式瞄准镜"游侠"',
        'optic_variable_sniper': '4 倍至 8 倍可调节式狙击手',
        'optic_digital_threat': '单倍数字化威胁',
        'optic_digital_sniper_threat': '4 倍至 10 倍数字化狙击威胁',
        # Hop_Ups
        'anvil_receiver': '铁砧接收器',
        'double_tap_trigger': '双发扳机',
        'skullpiercer_rifling': '穿颅器',
        'turbocharger': '涡轮增压器',
        # Stocks
        'standard_stock': '标准枪托',
        'sniper_stock': '狙击枪枪托',
        # Gear
        'helmet': '头盔',
        'evo_shield': '进化护盾',
        'knockdown_shield': '击倒护盾',
        'backpack': '背包',
        'survival': '隔热板',
        'mobile_respawn_beacon': '移动重生信标',
        # Regen
        'shield_cell': '小型护盾电池',
        'syringe': '注射器',
        'large_shield_cell': '护盾电池',
        'med_kit': '医疗箱',
        'phoenix_kit': '凤凰治疗包',
        'ultimate_accelerant': '绝招加速剂',
        # Ammo
        'special': '特殊弹药',
        'energy': '能量弹药',
        'heavy': '重型弹药',
        'light': '轻型弹药',
        'shotgun': '霰弹枪弹药',
        'sniper': '狙击弹药',
        # Other
        'evo_points': '进化点数',
        'Rare': '稀有',
        'Epic': '史诗',
        # Rank
        'Unranked': '菜鸟',
        'Bronze': '青铜',
        'Silver': '白银',
        'Gold': '黄金',
        'Platinum': '白金',
        'Diamond': '钻石',
        'Master': '大师',
        'Apex Predator': 'APEX 猎杀者',
        # Legends
        'Bloodhound': '寻血猎犬',
        'Gibraltar': '直布罗陀',
        'Lifeline': '命脉',
        'Pathfinder': '探路者',
        'Wraith': '恶灵',
        'Bangalore': '班加罗尔',
        'Caustic': '侵蚀',
        'Mirage': '幻象',
        'Octane': '动力小子',
        'Wattson': '沃特森',
        'Crypto': '密客',
        'Revenant': '亡灵',
        'Loba': '罗芭',
        'Rampart': '兰伯特',
        'Horizon': '地平线',
        'Fuse': '暴雷',
        'Valkyrie': '瓦尔基里',
        'Seer': '希尔',
        'Ash': '艾许',
        'Mad Maggie': '疯玛吉',
        'Newcastle': '纽卡斯尔',
        'Vantage': '万蒂奇',
        'Catalyst': '卡特莉丝',
        'Ballistic': '弹道',
        # Level
        'Common': '等级1',
        'Rare': '等级2',
        'Epic': '等级3',
        'Legendary': '等级4',
        'Mythic': '等级5',
        # Weapon
        ## ARs
        'havoc': '哈沃克步枪',
        'flatline': 'VK-47 平行步枪',
        'hemlok': '赫姆洛克连发突击步枪',
        'r-301': 'R-301 卡宾枪',
        'nemesis': '复仇女神连发突击步枪',
        ## SMGs
        'alternator': '转换者冲锋枪',
        'prowler': '猎兽冲锋枪',
        'r-99': 'R-99 冲锋枪',
        'volt': '电能冲锋枪',
        'car': 'C.A.R 冲锋枪',
        ## LMGs
        'devotion': '专注轻机枪',
        'l-star': 'L-STAR 能量机枪',
        'spitfire': 'M600 喷火轻机枪',
        'rampage': '暴走',
        ## Marksman
        'g7-scout': 'G7 侦察枪',
        'triple-take': '三重式狙击枪',
        '30-30 Repeater': '30-30 连发枪',
        'bow': '波塞克复合弓',
        ## Snipers
        'charge-rifle': '充能步枪',
        'longbow': '长弓精确步枪',
        'kraber': '克雷贝尔 50口径狙击枪',
        'sentinel': '哨兵狙击步枪',
        ## Shotguns
        'eva': 'EVA-8自动霰弹枪',
        'mastiff': '敖犬霰弹枪',
        'mozambique': '莫桑比克',
        'peacekeeper': '和平捍卫者霰弹枪',
        ## Pistols
        'RE-45': 'RE-45 自动手枪',
        'p2020': 'P2020手枪',
        'wingman': '辅助手枪',
        # API
        'offline': '离线',
        'online': '在线',
        0: '否',
        1: '是',
        'invite': '邀请',
        'open': '打开',
        'inLobby': '在大厅',
        'inMatch': '比赛中',
        'true': '是',
        'false': '否'
    }
    return names.get(name, name)
