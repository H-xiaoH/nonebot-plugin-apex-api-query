from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupMessageEvent, GROUP, GROUP_ADMIN, GROUP_OWNER
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.permission import SUPERUSER
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_txt2img import Txt2Img
from httpx import AsyncClient
from .config import Config

__plugin_meta__ = PluginMetadata(
    'Apex API Query',
    'Apex Legends API 查询插件',
    '''
    /bridge [玩家名称] -根据玩家名称玩家信息, 
    /uid [玩家UID] -根据玩家UID查询玩家信息, 
    /maprotation -查询地图轮换, 
    /predator -查询顶尖猎杀者, 
    /crafting -查询制造轮换, 
    /submap -订阅地图轮换[每整点查询], 
    /subcraft -订阅制造轮换[每日2时查询]
    '''
)

plugin_config = Config.parse_obj(get_driver().config)

api_key = plugin_config.apex_api_key
api_url = plugin_config.apex_api_url

player_statistics = on_command('bridge', aliases= {'玩家'})
uid_statistics = on_command('uid', aliases={'UID'})
map_protation = on_command('maprotation', aliases={'地图'})
predator = on_command('predator', aliases={'猎杀'})
crafting_rotation = on_command('crafting', aliases={'制造'})
servers = on_command('servers', aliases={'服务'})
sub_map = on_command('submap', aliases={'订阅地图'}, permission=GROUP and SUPERUSER | GROUP_ADMIN | GROUP_OWNER)
unsub_map = on_command('unsubmap', aliases={'取消订阅地图'}, permission=GROUP and SUPERUSER | GROUP_ADMIN | GROUP_OWNER)
sub_craft = on_command('subcraft', aliases={'订阅制造'}, permission=GROUP and SUPERUSER | GROUP_ADMIN | GROUP_OWNER)
unsub_craft = on_command('unsubcraft', aliases={'取消订阅制造'}, permission=GROUP and SUPERUSER | GROUP_ADMIN | GROUP_OWNER)

# 玩家名称查询
@player_statistics.handle()
async def _(player_name: Message = CommandArg()):
    service = 'bridge'
    payload = {'auth': api_key, 'player': str(player_name), 'platform': 'PC'}
    await player_statistics.send('正在查询: 玩家 {}'.format(player_name))
    response = await api_query(service, payload)
    font_size = 32
    title = '玩家 {}'.format(player_name)
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await player_statistics.send(msg)

# 玩家 UID 查询
@uid_statistics.handle()
async def _(player_name: Message = CommandArg()):
    service = 'bridge'
    payload = {'auth': api_key, 'uid': str(player_name), 'platform': 'PC'}
    await uid_statistics.send('正在查询: UID {}'.format(player_name))
    response = await api_query(service, payload)
    font_size = 32
    title = 'UID {}'.format(player_name)
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await uid_statistics.send(msg)

# 地图轮换查询
@map_protation.handle()
async def _():
    service = 'maprotation'
    payload = {'auth': api_key, 'version': '2'}
    await map_protation.send('正在查询: 地图轮换')
    response = await api_query(service, payload)
    font_size = 32
    title = '地图轮换'
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await map_protation.send(msg)

# 顶尖猎杀者查询
@predator.handle()
async def _():
    service = 'predator'
    payload = {'auth': api_key}
    await predator.send('正在查询: 顶尖猎杀者')
    response = await api_query(service, payload)
    font_size = 32
    title = '顶尖猎杀者'
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await predator.send(msg)

# 制造轮换查询
@crafting_rotation.handle()
async def _():
    service = 'crafting'
    payload = {'auth': api_key}
    await crafting_rotation.send('正在查询: 制造轮换')
    response = await api_query(service, payload)
    font_size = 32
    title = '制造轮换'
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await crafting_rotation.send(msg)

# 服务器状态查询
@servers.handle()
async def _():
    service = 'servers'
    payload = {'auth': api_key}
    await servers.send('正在查询: 服务器状态')
    response = await api_query(service, payload)
    font_size = 32
    title = '服务器状态'
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await servers.send(msg)

# 订阅地图轮换
@sub_map.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    try:
        scheduler.add_job(func=submap, trigger='cron', id=(str(event.group_id) + '_map'), minute=1, kwargs={'bot': bot, 'group_id': event.group_id})
        await sub_map.send('已订阅地图轮换')
    except BaseException as err:
        await sub_map.send('订阅地图轮换失败: {}'.format(err))

# 地图轮换定时任务
async def submap(bot, group_id):
    service = 'maprotation'
    payload = {'auth': api_key, 'version': '2'}
    await bot.send_group_msg(group_id=group_id, message='正在查询: 地图轮换')
    response = await api_query(service, payload)
    font_size = 32
    title = '地图轮换'
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await bot.send_group_msg(group_id=group_id, message=msg)

# 取消订阅地图轮换
@unsub_map.handle()
async def _(event: GroupMessageEvent):
    try:
        scheduler.remove_job(job_id=(str(event.group_id) + '_map'))
        await unsub_map.send('已取消订阅地图轮换')
    except BaseException as err:
        await unsub_map.send('取消订阅地图轮换失败: {}'.format(err))

# 订阅制造轮换
@sub_craft.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    try:
        scheduler.add_job(func=subcraft, trigger='cron', id=(str(event.group_id) + '_craft'), hour=2, minute=1, kwargs={'bot': bot, 'group_id': event.group_id})
        await sub_craft.send('已订阅制造轮换')
    except BaseException as err:
        await sub_craft.send('订阅制造轮换失败: {}'.format(err))

# 制造轮换定时任务
async def subcraft(bot, group_id):
    service = 'crafting'
    payload = {'auth': api_key}
    await bot.send_group_msg(group_id=group_id, message='正在查询: 制造轮换')
    response = await api_query(service, payload)
    font_size = 32
    title = '制造轮换'
    text = response
    img = Txt2Img(font_size)
    pic = img.save(title, text)
    msg = MessageSegment.image(pic)
    await bot.send_group_msg(group_id=group_id, message=msg)

# 取消订阅制造轮换
@unsub_craft.handle()
async def _(event: GroupMessageEvent):
    try:
        scheduler.remove_job(job_id=(str(event.group_id) + '_craft'))
        await unsub_craft.send('已取消订阅制造轮换')
    except BaseException as err:
        await unsub_craft.send('取消订阅制造轮换失败: {}'.format(err))

# 异步查询
async def api_query(service, payload):
    try:
        async with AsyncClient() as client:
            response = await client.get(api_url + service, params = payload, timeout = None)
        if response.status_code != 200 or response.text.find('Error') != -1:
            data = '查询失败: API 错误: {}'.format(response.text)
        else:
            data = process(service, response)
        return data
    except BaseException as err:
        data = '查询失败: 网络错误: {}'.format(err)
        return data

# 处理获取信息
def process(service, response):

    # 玩家数据
    if service == 'bridge':
        globals = response.json().get('global')
        realtime = response.json().get('realtime')
        data = (
            '玩家信息:\n'
            '名称: {}\n'
            'UID: {}\n'
            '平台: {}\n'
            '等级: {}\n'
            '距下一级百分比: {}%\n'
            '封禁状态: {}\n'
            '剩余秒数: {}\n'
            '最后封禁原因: {}\n'
            '大逃杀分数: {}\n'
            '大逃杀段位: {} {}\n'
            '竞技场分数: {}\n'
            '竞技场段位: {} {}\n'
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
                globals.get('toNextLevelPercent'),
                convert(globals.get('bans').get('isActive')),
                globals.get('bans').get('remainingSeconds'),
                convert(globals.get('bans').get('last_banReason')),
                globals.get('rank').get('rankScore'),
                convert(globals.get('rank').get('rankName')),
                globals.get('rank').get('rankDiv'),
                globals.get('arena').get('rankScore'),
                convert(globals.get('arena').get('rankName')),
                globals.get('arena').get('rankDiv'),
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

    # 地图轮换数据
    elif service == 'maprotation':
        battle_royale = response.json().get('battle_royale')
        arenas = response.json().get('arenas')
        ranked = response.json().get('ranked')
        arenasRanked = response.json().get('arenasRanked')
        data = (
            '大逃杀:\n'
            '当前地图: {}\n'
            '下个地图: {}\n'
            '剩余时间: {}\n\n'
            '竞技场:\n'
            '当前地图: {}\n'
            '下个地图: {}\n'
            '剩余时间: {}\n\n'
            '排位赛联盟:\n'
            '当前地图: {}\n'
            '下个地图: {}\n'
            '剩余时间: {}\n\n'
            '排位竞技场:\n'
            '当前地图: {}\n'
            '下个地图: {}\n'
            '剩余时间: {}'
            .format(
                convert(battle_royale.get('current').get('map')),
                convert(battle_royale.get('next').get('map')),
                convert(battle_royale.get('current').get('remainingTimer')),
                convert(arenas.get('current').get('map')),
                convert(arenas.get('next').get('map')),
                convert(arenas.get('current').get('remainingTimer')),
                convert(ranked.get('current').get('map')),
                convert(ranked.get('next').get('map')),
                convert(ranked.get('current').get('remainingTimer')),
                convert(arenasRanked.get('current').get('map')),
                convert(arenasRanked.get('next').get('map')),
                convert(arenasRanked.get('current').get('remainingTimer'))
            )
        )
        return data

    # 顶尖猎杀者数据
    elif service == 'predator':
        rp = response.json().get('RP')
        ap = response.json().get('AP')
        data = (
            '大逃杀:\n'
            'PC 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}\n'
            'PS4/5 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}\n'
            'Xbox 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}\n'
            'Switch 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}\n\n'
            '竞技场:\n'
            'PC 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}\n'
            'PS4/5 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}\n'
            'Xbox 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}\n'
            'Switch 端:\n'
            '顶尖猎杀者人数: {}\n'
            '顶尖猎杀者分数: {}\n'
            '顶尖猎杀者UID: {}\n'
            '大师和顶尖猎杀者人数: {}'
            .format(
                rp.get('PC').get('foundRank'),
                rp.get('PC').get('val'),
                rp.get('PC').get('uid'),
                rp.get('PC').get('totalMastersAndPreds'),
                rp.get('PS4').get('foundRank'),
                rp.get('PS4').get('val'),
                rp.get('PS4').get('uid'),
                rp.get('PS4').get('totalMastersAndPreds'),
                rp.get('X1').get('foundRank'),
                rp.get('X1').get('val'),
                rp.get('X1').get('uid'),
                rp.get('X1').get('totalMastersAndPreds'),
                rp.get('SWITCH').get('foundRank'),
                rp.get('SWITCH').get('val'),
                rp.get('SWITCH').get('uid'),
                rp.get('SWITCH').get('totalMastersAndPreds'),
                ap.get('PC').get('foundRank'),
                ap.get('PC').get('val'),
                ap.get('PC').get('uid'),
                ap.get('PC').get('totalMastersAndPreds'),
                ap.get('PS4').get('foundRank'),
                ap.get('PS4').get('val'),
                ap.get('PS4').get('uid'),
                ap.get('PS4').get('totalMastersAndPreds'),
                ap.get('X1').get('foundRank'),
                ap.get('X1').get('val'),
                ap.get('X1').get('uid'),
                ap.get('X1').get('totalMastersAndPreds'),
                ap.get('SWITCH').get('foundRank'),
                ap.get('SWITCH').get('val'),
                ap.get('SWITCH').get('uid'),
                ap.get('SWITCH').get('totalMastersAndPreds')
            )
        )
        return data

    # 制造数据
    elif service == 'crafting':
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
    
    # 服务器数据
    elif service == 'servers':
        data = (
            'Origin 登录:\n'
            '欧盟西部: {}\n'
            '欧盟东部: {}\n'
            '美国西部: {}\n'
            '美国中部: {}\n'
            '美国东部: {}\n'
            '南美洲: {}\n'
            '亚洲: {}\n\n'
            'EA 融合:\n'
            '欧盟西部: {}\n'
            '欧盟东部: {}\n'
            '美国西部: {}\n'
            '美国中部: {}\n'
            '美国东部: {}\n'
            '南美洲: {}\n'
            '亚洲: {}\n\n'
            'EA 账户:\n'
            '欧盟西部: {}\n'
            '欧盟东部: {}\n'
            '美国西部: {}\n'
            '美国中部: {}\n'
            '美国东部: {}\n'
            '南美洲: {}\n'
            '亚洲: {}\n\n'
            'Apex 跨平台验证:\n'
            '欧盟西部: {}\n'
            '欧盟东部: {}\n'
            '美国西部: {}\n'
            '美国中部: {}\n'
            '美国东部: {}\n'
            '南美洲: {}\n'
            '亚洲: {}\n\n'
            '自我核心测试:\n'
            '网站状态: {}\n'
            '统计API: {}\n'
            '溢出 #1: {}\n'
            '溢出 #2: {}\n'
            'Origin API: {}\n'
            'Playstation API: {}\n'
            'Xbox API: {}\n\n'
            '其他平台:\n'
            'Playstation Network: {}\n'
            'Xbox Live: {}\n\n'
            'Data from apexlegendsstatus.com'
            .format(
                convert(response.json().get('Origin_login').get('EU-West').get('Status')),
                convert(response.json().get('Origin_login').get('EU-East').get('Status')),
                convert(response.json().get('Origin_login').get('US-West').get('Status')),
                convert(response.json().get('Origin_login').get('US-Central').get('Status')),
                convert(response.json().get('Origin_login').get('US-East').get('Status')),
                convert(response.json().get('Origin_login').get('SouthAmerica').get('Status')),
                convert(response.json().get('Origin_login').get('Asia').get('Status')),
                convert(response.json().get('EA_novafusion').get('EU-West').get('Status')),
                convert(response.json().get('EA_novafusion').get('EU-East').get('Status')),
                convert(response.json().get('EA_novafusion').get('US-West').get('Status')),
                convert(response.json().get('EA_novafusion').get('US-Central').get('Status')),
                convert(response.json().get('EA_novafusion').get('US-East').get('Status')),
                convert(response.json().get('EA_novafusion').get('SouthAmerica').get('Status')),
                convert(response.json().get('EA_novafusion').get('Asia').get('Status')),
                convert(response.json().get('EA_accounts').get('EU-West').get('Status')),
                convert(response.json().get('EA_accounts').get('EU-East').get('Status')),
                convert(response.json().get('EA_accounts').get('US-West').get('Status')),
                convert(response.json().get('EA_accounts').get('US-Central').get('Status')),
                convert(response.json().get('EA_accounts').get('US-East').get('Status')),
                convert(response.json().get('EA_accounts').get('SouthAmerica').get('Status')),
                convert(response.json().get('EA_accounts').get('Asia').get('Status')),
                convert(response.json().get('ApexOauth_Crossplay').get('EU-West').get('Status')),
                convert(response.json().get('ApexOauth_Crossplay').get('EU-East').get('Status')),
                convert(response.json().get('ApexOauth_Crossplay').get('US-West').get('Status')),
                convert(response.json().get('ApexOauth_Crossplay').get('US-Central').get('Status')),
                convert(response.json().get('ApexOauth_Crossplay').get('US-East').get('Status')),
                convert(response.json().get('ApexOauth_Crossplay').get('SouthAmerica').get('Status')),
                convert(response.json().get('ApexOauth_Crossplay').get('Asia').get('Status')),
                convert(response.json().get('selfCoreTest').get('Status-website').get('Status')),
                convert(response.json().get('selfCoreTest').get('Stats-API').get('Status')),
                convert(response.json().get('selfCoreTest').get('Overflow-#1').get('Status')),
                convert(response.json().get('selfCoreTest').get('Overflow-#2').get('Status')),
                convert(response.json().get('selfCoreTest').get('Origin-API').get('Status')),
                convert(response.json().get('selfCoreTest').get('Playstation-API').get('Status')),
                convert(response.json().get('selfCoreTest').get('Xbox-API').get('Status')),
                convert(response.json().get('otherPlatforms').get('Playstation-Network').get('Status')),
                convert(response.json().get('otherPlatforms').get('Xbox-Live').get('Status'))
            )
        )
        return data

# 请求内容转换
def convert(name):
    names = {
        # Map
        'Kings Canyon': '诸王峡谷',
        'World\'s Edge': '世界尽头',
        'Olympus': '奥林匹斯',
        'Storm Point': '风暴点',
        'Broken Moon': '破碎月亮',
        'Encore': '再来一次',
        'Habitat': '栖息地 4',
        'Overflow': '熔岩流',
        'Phase runner': '相位穿梭器',
        'Party crasher': '派对破坏者',
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
        'Apex Predator': 'Apex 猎杀者',
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
        # Level
        'Common': '等级1',
        'Rare': '等级2',
        'Epic': '等级3',
        'Legendary': '等级4',
        'Mythic': '等级5',
        # Weapon
        'peacekeeper': '和平捍卫者',
        'spitfire': '喷火轻机枪',
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
        'false': '否',
        'COMPETITIVE_DODGE_COOLDOWN': '竞技逃跑冷却',
        'None': '无',
        'EU-West': '欧盟西部',
        'EU-East': '欧盟东部',
        'US-West': '美国西部',
        'US-Central': '美国中部',
        'US-East': '美国东部',
        'SouthAmerica': '南美洲',
        'Asia': '亚洲',
        'Status-website': '网站状态',
        'Stats-API': '统计API',
        'Overflow-#1': '溢出 #1',
        'Overflow-#2': '溢出 #2',
        'Origin-API': 'Origin API',
        'Playstation-API': 'Playstation API',
        'Xbox-API': 'Xbox API',
        'Playstation-Network': 'Playstation Network',
        'Xbox-Live': 'Xbox Live',
        'UP': '✔在线',
        'DOWN': '❌离线',
        'SLOW': '⚠缓慢',
        'OVERLOADED': '🚧过载',
    }
    return names.get(name, name)
