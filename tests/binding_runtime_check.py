"""Real Console commands and persistent bindings in ORM's localstore SQLite."""
import asyncio
from datetime import datetime
from itertools import count
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tests.bootstrap import DATABASE, p
import nonebot
from nonebot.adapters.console import Adapter, Bot
from nonebot.adapters.console.event import MessageEvent
from nonebot.adapters.console.message import Message
from nonechat.model import Robot, User, Channel
from nonebot_plugin_apex_api_query.bindings import get_binding, owner_key, refresh_binding_name
from sqlalchemy import func, select
from nonebot_plugin_apex_api_query.models import PlayerBinding


def player(uid, name, platform='PC'):
    return {'global': {'uid': uid, 'name': name, 'platform': platform, 'level': 1,
            'levelPrestige': 0, 'rank': {'rankName': 'Gold', 'rankDiv': 4, 'rankScore': 100}}}


async def main():
    driver = nonebot.get_driver()
    await driver._lifespan.startup()
    adapter = nonebot.get_adapter(Adapter)
    class Frontend:
        def __init__(self): self.sent = []
        async def send_message(self, **kwargs):
            self.sent.append(str(kwargs['content']))
            return str(len(self.sent))
    adapter._frontend = Frontend()
    bots = {}
    message_ids = count(1)
    def event(user='alice', channel='group'):
        return MessageEvent(time=datetime.now(), self_id='bot-a', user=User(user),
            channel=Channel(channel, channel), message_id=str(next(message_ids)), message=Message())
    async def command(text, user='alice', channel='group', bot_id='bot-a'):
        if bot_id not in bots:
            bots[bot_id] = Bot(adapter, Robot(bot_id))
            adapter.bot_connect(bots[bot_id])
        ev = event(user, channel)
        ev.self_id = bot_id
        ev.message = Message(text)
        ev.original_message = Message(text)
        adapter._frontend.sent.clear()
        await bots[bot_id].handle_event(ev)
        reply = '\n'.join(adapter._frontend.sent)
        print(text, '=>', reply, flush=True)
        assert reply, f'No reply for {text}'
        return reply
    players = {'Alpha': player('1001', 'Alpha'), 'Beta': player('1002', 'Beta'),
               '12345': player('1003', '12345'), 'Empty': player('1004', ''),
               'SwitchPlayer': player('1005', 'SwitchPlayer', 'SWITCH'),
               'ConsolePlayer': player('1006', 'ConsolePlayer', 'PS4')}
    calls = []
    async def fetch(endpoint, params=None):
        assert endpoint == 'bridge'
        calls.append(dict(params))
        if 'uid' in params:
            for data in players.values():
                if data['global']['uid'] == params['uid']:
                    return data
        elif params.get('player') in players:
            return players[params['player']]
        raise p.ApexAPIError('找不到玩家')
    try:
        with patch.object(p, '_fetch', AsyncMock(side_effect=fetch)), patch.object(p.config, 'apex_only_text', True):
            assert '绑定' in await command('/apex')
            assert '尚未绑定' in await command('/apex bind')
            assert '已绑定玩家' in await command('/apex bind Alpha pc')
            assert calls[-1] == {'platform': 'PC', 'player': 'Alpha'}
            assert 'UID: 1001' in await command('/apex bind')
            assert '名称: Alpha' in await command('/apex')
            assert calls[-1] == {'platform': 'PC', 'uid': '1001'}
            assert '名称: Alpha' in await command('/apex', channel='_direct')
            assert '请输入玩家名称' in await command('/apex', user='bob')
            assert '请输入玩家名称' in await command('/apex', bot_id='bot-b')
            assert '名称: Beta' in await command('/apex Beta')  # One-off lookup does not replace binding.
            assert 'UID: 1001' in await command('/apex bind')
            assert '找不到玩家' in await command('/apex bind Missing')
            assert 'UID: 1001' in await command('/apex bind')
            assert 'UID 格式错误' in await command('/apex binduid not-a-uid')
            assert '请输入 UID' in await command('/apex binduid')
            assert '平台参数错误' in await command('/apex bind Alpha BAD')
            assert 'UID: 1001' in await command('/apex bind')
            players['Alpha']['global']['name'] = 'Renamed'
            assert '名称: Renamed' in await command('/apex')
            assert calls[-1] == {'platform': 'PC', 'uid': '1001'}
            assert '玩家: Renamed' in await command('/apex bind')
            assert '已绑定玩家' in await command('.apex 绑定UID 1002')
            assert calls[-1] == {'platform': 'PC', 'uid': '1002'}
            owner = owner_key(bots['bot-a'], event())
            await refresh_binding_name(owner, '1001', 'PC', 'Stale')
            assert (await get_binding(owner)).uid == '1002'
            assert (await get_binding(owner)).player_name == 'Beta'
            assert '已绑定玩家' in await command('/apex bind 12345', user='bob')
            assert calls[-1] == {'platform': 'PC', 'player': '12345'}
            assert 'UID: 1003' in await command('/apex 绑定', user='bob')
            assert '已绑定玩家' in await command('/apex bind Empty', user='carol')
            assert '名称: Empty' in await command('/apex', user='carol')
            assert '已解除' in await command('/apex 解绑', user='carol')
            assert '尚未绑定' in await command('/apex unbind', user='carol')
            assert '请输入玩家名称' in await command('/apex', user='carol')
            assert '已解除' in await command('/apex unbind', user='bob')
            assert 'UID: 1002' in await command('/apex bind')
            assert '已绑定玩家' in await command('/apex binduid 1005 switch', user='dave')
            assert '平台: SWITCH' in await command('/apex', user='dave')
            assert calls[-1] == {'platform': 'SWITCH', 'uid': '1005'}
            assert 'Switch 玩家请使用' in await command('/apex bind SwitchPlayer SWITCH', user='dave')
            assert 'UID: 1005' in await command('/apex bind', user='dave')
            assert '已解除' in await command('/apex unbind', user='dave')
            assert '已绑定玩家' in await command('/apex bind ConsolePlayer PS4', user='eve')
            assert '平台: PS4' in await command('/apex', user='eve')
            assert '已解除' in await command('/apex unbind', user='eve')
            # Hold the first validation while a rebind or unbind arrives.
            for unbind in (False, True):
                started, release = asyncio.Event(), asyncio.Event()
                async def delayed(name, platform, **kwargs):
                    if name == 'Slow':
                        started.set()
                        await release.wait()
                    return '', {'uid': '2001' if name == 'Slow' else '2002',
                                'name': name, 'platform': platform}
                ev = event('racing-user')
                owner = owner_key(bots['bot-a'], ev)
                with patch.object(p, 'get_player_stats', delayed):
                    slow = asyncio.create_task(p._bind_account(AsyncMock(), bots['bot-a'], ev, 'Slow', 'PC'))
                    await started.wait()
                    later = asyncio.create_task(p.delete_binding(owner) if unbind else
                        p._bind_account(AsyncMock(), bots['bot-a'], ev, 'Fast', 'PC'))
                    await asyncio.sleep(0)
                    release.set()
                    await asyncio.gather(slow, later)
                binding = await get_binding(owner)
                assert binding is None if unbind else binding.player_name == 'Fast'
                await p.delete_binding(owner)
            async with p.get_session() as session:
                assert await session.scalar(select(func.count()).select_from(PlayerBinding)) == 1
                connection = await session.connection()
                assert Path(connection.engine.url.database).resolve() == DATABASE.resolve()
            # Real shutdown/startup reconstructs the ORM engines from disk.
            await driver._lifespan.shutdown()
            import nonebot_plugin_orm as orm
            for engine in orm._engines.values():
                await engine.dispose()
            await driver._lifespan.startup()
            assert 'UID: 1002' in await command('/apex bind')
            assert '名称: Beta' in await command('/apex')
        print('PASS name/UID binding, user/bot isolation, rename, rebind, unbind, restart and localstore database')
    finally:
        for bot in bots.values():
            adapter.bot_disconnect(bot)
        await driver._lifespan.shutdown()
        import nonebot_plugin_orm as orm
        for engine in orm._engines.values():
            await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
