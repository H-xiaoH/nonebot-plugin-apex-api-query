from typing import Any

VALID_PLATFORMS: list[str] = ["PC", "PS4", "X1", "SWITCH"]

DEFAULT_PLATFORM: str = "PC"

PLATFORM_DISPLAY: dict[str, str] = {
    "PC": "PC 端",
    "PS4": "PS4/5 端",
    "X1": "Xbox 端",
    "SWITCH": "Switch 端",
}


SERVER_SECTIONS: dict[str, str] = {
    "Origin 登录": "Origin_login",
    "EA 融合": "EA_novafusion",
    "EA 账户": "EA_accounts",
    "Apex 跨平台验证": "ApexOauth_Crossplay",
    "自我核心测试": "selfCoreTest",
    "其他平台": "otherPlatforms",
}


SERVER_REGIONS: dict[str, str] = {
    "欧盟西部": "EU-West",
    "欧盟东部": "EU-East",
    "美国西部": "US-West",
    "美国中部": "US-Central",
    "美国东部": "US-East",
    "南美洲": "SouthAmerica",
    "亚洲": "Asia",
}


SELF_CORE_TESTS: dict[str, str] = {
    "网站状态": "Status-website",
    "统计 API": "Stats-API",
    "溢出 #1": "Overflow-#1",
    "溢出 #2": "Overflow-#2",
    "Origin API": "Origin-API",
    "Playstation API": "Playstation-API",
    "Xbox API": "Xbox-API",
}


OTHER_PLATFORMS: dict[str, str] = {
    "Playstation Network": "Playstation-Network",
    "Xbox Live": "Xbox-Live",
}


MAP_TRANSLATIONS: dict[str, str] = {
    "Kings Canyon": "诸王峡谷",
    "World's Edge": "世界尽头",
    "Olympus": "奥林匹斯",
    "Storm Point": "风暴点",
    "Broken Moon": "残月",
    "Encore": "再来一次",
    "Habitat": "栖息地",
    "Overflow": "熔岩流",
    "Phase runner": "相位穿梭器",
    "Party crasher": "派对破坏者",
    "Drop Off": "原料场",
    "Skulltown": "骷髅镇",
    "Barometer": "气压计",
    "Wall": "高墙",
    "Siphon": "岩浆汲取器",
    "Fragment": "碎片东部",
    "E-District": "电力区域",
    "The Core": "核心",
    "Monument": "纪念碑",
    "Thunderdome": "雷霆圆顶",
    "Hammond Labs": "哈蒙德实验室",
    "Estates": "不动产",
    "Unknown": "未知",
    "None": "无",
}

WEAPON_TRANSLATIONS: dict[str, str] = {
    # 突击步枪
    "havoc": "哈沃克步枪",
    "flatline": "平行步枪",
    "hemlok": "赫姆洛克突击步枪",
    "r-301": "R-301 卡宾枪",
    "nemesis": "复仇女神",
    # 冲锋枪
    "alternator": "转换者冲锋枪",
    "prowler": "猎兽冲锋枪",
    "r-99": "R-99 冲锋枪",
    "volt": "电能冲锋枪",
    "car": "CAR",
    # 轻机枪
    "devotion": "专注轻机枪",
    "l-star": "L-STAR 能量机枪",
    "spitfire": "喷火轻机枪",
    "rampage": "暴走",
    # 神射手
    "g7-scout": "G7 侦察枪",
    "triple-take": "三重式狙击枪",
    "repeater": "30-30",
    "bow": "波塞克",
    # 狙击枪
    "charge-rifle": "充能步枪",
    "longbow": "长弓",
    "kraber": "克雷贝尔狙击枪",
    "sentinel": "哨兵狙击步枪",
    # 霰弹枪
    "eva": "EVA-8",
    "mastiff": "敖犬霰弹枪",
    "mozambique": "莫桑比克",
    "peacekeeper": "和平捍卫者",
    # 手枪
    "re-45": "RE-45 自动手枪",
    "p2020": "P2020 手枪",
    "wingman": "辅助手枪"
}

LEGEND_TRANSLATIONS: dict[str, str] = {
    # 突击位
    "Bangalore": "班加罗尔",
    "Revenant": "亡灵",
    "Fuse": "暴雷",
    "Mad Maggie": "疯玛吉",
    "Ballstic": "弹道",
    # 游击位
    "Pathfinder": "探路者",
    "Wraith": "恶灵",
    "Octane": "动力小子",
    "Horizon": "地平线",
    "Ash": "艾许",
    "Alter": "变幻",
    "Axle": "艾克塞尔",
    # 侦查位
    "Bloodhound": "寻血猎犬",
    "Crypto": "密客",
    "Valkyrie": "瓦尔基里",
    "Seer": "希尔",
    "Vantage": "万蒂奇",
    "Sparrow": "硫雀",
    # 支援位
    "Gibraltar": "直布罗陀",
    "Lifeline": "命脉",
    "Mirage": "幻象",
    "Loba": "罗芭",
    "Newcastle": "纽卡斯尔",
    "Conduit": "导线管",
    # 控制位
    "Caustic": "侵蚀",
    "Wattson": "沃特森",
    "Rampart": "兰伯特",
    "Catalyst": "卡特莉丝"
}

RANK_TRANSLATIONS: dict[str, str] = {
    "Unranked": "无段位",
    "Rookie": "菜鸟",
    "Bronze": "青铜",
    "Silver": "白银",
    "Gold": "黄金",
    "Platinum": "白金",
    "Diamond": "钻石",
    "Master": "大师",
    "Apex Predator": "Apex 猎杀者",
}

RARITY_TRANSLATIONS: dict[str, str] = {
    "Common": "等级1",
    "Rare": "等级2",
    "Epic": "等级3",
    "Legendary": "等级4",
    "Mythic": "等级5",
}

BARREL_TRANSLATIONS: dict[str, str] = {
    "barrel_stabilizer": "枪管稳定器",
    "laser_sight": "激光瞄准镜",
}

MAGAZINE_TRANSLATIONS: dict[str, str] = {
    "extended_energy_mag": "加长式能量弹匣",
    "extended_heavy_mag": "加长式重型弹匣",
    "extended_light_mag": "加长式轻型弹匣",
    "extended_sniper_mag": "加长狙击弹匣",
    "shotgun_bolt": "霰弹枪枪栓",
}

OPTIC_TRANSLATIONS: dict[str, str] = {
    "optic_hcog_classic": '单倍全息衍射式瞄准镜"经典"',
    "optic_holo": "单倍幻影",
    "optic_variable_holo": "单倍至 2 倍可调节式幻影瞄准镜",
    "optic_hcog_bruiser": '2 倍全息衍射式瞄准镜"格斗家"',
    "optic_sniper": "6 倍狙击手",
    "optic_variable_aog": "2 倍至 4 倍可调节式高级光学瞄准镜",
    "optic_hcog_ranger": '3 倍全息衍射式瞄准镜"游侠"',
    "optic_variable_sniper": "4 倍至 8 倍可调节式狙击手",
    "optic_digital_threat": "单倍数字化威胁",
    "optic_digital_sniper_threat": "4 倍至 10 倍数字化狙击威胁",
}

HOPUP_TRANSLATIONS: dict[str, str] = {
    "anvil_receiver": "铁砧接收器",
    "double_tap_trigger": "双发扳机",
    "skullpiercer_rifling": "穿颅器",
    "turbocharger": "涡轮增压器",
}

STOCK_TRANSLATIONS: dict[str, str] = {
    "standard_stock": "标准枪托",
    "sniper_stock": "狙击枪枪托",
}

ATTACHMENT_TRANSLATIONS: dict[str, str] = {
    **BARREL_TRANSLATIONS,
    **MAGAZINE_TRANSLATIONS,
    **OPTIC_TRANSLATIONS,
    **HOPUP_TRANSLATIONS,
    **STOCK_TRANSLATIONS,
}

ARMOR_TRANSLATIONS: dict[str, str] = {
    "helmet": "头盔",
    "evo_shield": "进化护盾",
    "knockdown_shield": "击倒护盾",
    "backpack": "背包",
}

EQUIPMENT_TRANSLATIONS: dict[str, str] = {
    "survival": "隔热板",
    "mobile_respawn_beacon": "移动重生信标",
}

CONSUMABLE_TRANSLATIONS: dict[str, str] = {
    "shield_cell": "小型护盾电池",
    "syringe": "注射器",
    "large_shield_cell": "护盾电池",
    "med_kit": "医疗箱",
    "phoenix_kit": "凤凰治疗包",
    "ultimate_accelerant": "绝招加速剂",
}

AMMO_TRANSLATIONS: dict[str, str] = {
    "special": "特殊弹药",
    "energy": "能量弹药",
    "heavy": "重型弹药",
    "light": "轻型弹药",
    "shotgun": "霰弹枪弹药",
    "sniper": "狙击弹药",
}

ITEM_TRANSLATIONS: dict[str, str] = {
    **ARMOR_TRANSLATIONS,
    **EQUIPMENT_TRANSLATIONS,
    **CONSUMABLE_TRANSLATIONS,
    **AMMO_TRANSLATIONS,
    "evo_points": "进化点数",
}

STATUS_TRANSLATIONS: dict[str, str] = {
    "offline": "离线",
    "online": "在线",
    "invite": "邀请",
    "open": "打开",
    "inLobby": "在大厅",
    "inMatch": "比赛中",
}

SERVER_STATUS_TRANSLATIONS: dict[str, str] = {
    "UP": "在线",
    "DOWN": "离线",
    "SLOW": "缓慢",
    "OVERLOADED": "过载",
}

BAN_TRANSLATIONS: dict[str, str] = {
    "COMPETITIVE_DODGE_COOLDOWN": "竞技逃跑冷却",
}

BOOLEAN_TRANSLATIONS: dict[Any, str] = {
    0: "否",
    1: "是",
    "true": "是",
    "false": "否",
}

TRANSLATIONS: dict[Any, str] = {
    **MAP_TRANSLATIONS,
    **WEAPON_TRANSLATIONS,
    **LEGEND_TRANSLATIONS,
    **RANK_TRANSLATIONS,
    **RARITY_TRANSLATIONS,
    **ATTACHMENT_TRANSLATIONS,
    **ITEM_TRANSLATIONS,
    **STATUS_TRANSLATIONS,
    **SERVER_STATUS_TRANSLATIONS,
    **BAN_TRANSLATIONS,
    **BOOLEAN_TRANSLATIONS,
}


def convert(name: Any) -> Any:
    """通用翻译：从完整翻译表中查找对应中文。若未收录则原样返回。

    Args:
        name: 英文 key，可以是字符串、整数等任意类型。

    Returns:
        中文翻译文本；key 不在翻译表中时原样返回输入值。
    """
    return TRANSLATIONS.get(name, name)


