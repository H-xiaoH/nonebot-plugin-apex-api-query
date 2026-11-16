"""Subprocess integration check: real startup, legacy schema, ORM and dispatch."""
import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from tests.bootstrap import DATABASE, p
import nonebot
from nonebot.adapters.console import Adapter, Bot
from nonebot.adapters.console.event import MessageEvent
from nonebot.adapters.console.message import Message
from nonechat.model import Robot, User, Channel
from sqlalchemy import func, select

# The previous release's schema, with a real historical row to preserve.
with sqlite3.connect(DATABASE) as db:
    db.executescript('''
    CREATE TABLE apex_player_stats (
        id INTEGER PRIMARY KEY, uid VARCHAR NOT NULL, player_name VARCHAR NOT NULL,
        platform VARCHAR NOT NULL, level INTEGER NOT NULL, rank_score INTEGER NOT NULL,
        rank_name VARCHAR NOT NULL, rank_div INTEGER, created_at DATETIME NOT NULL);
    CREATE INDEX idx_uid_platform ON apex_player_stats(uid, platform);
    INSERT INTO apex_player_stats VALUES
        (1, 'legacy', 'Legacy', 'PC', 500, 100, '青铜', 4, '2026-01-01 00:00:00');
    ''')


async def main():
    driver = nonebot.get_driver()
    await driver._lifespan.startup()
    try:
        old = await p.get_latest_record('legacy', 'PC')
        assert old is not None and old.prestige is None and old.level == 500
        first = await p._compare_and_save('legacy', 'PC', 'Legacy', 1, 100, '青铜', 4, '等级: 1', prestige=1)
        assert '等级' not in first[0]  # Old rows have no reliable prestige baseline.
        next_ = await p._compare_and_save('legacy', 'PC', 'Legacy', 2, 100, '青铜', 4, '等级: 2', prestige=1)
        assert next_[0]['等级'] == '(↑1)'
        await p.save_record('cycle', 'Cycle', 'PC', p.PlayerStatsData(500, 100, '青铜', 4, prestige=0))
        cycle = await p._compare_and_save('cycle', 'PC', 'Cycle', 1, 100, '青铜', 4, '等级: 1', prestige=1)
        assert cycle[0]['等级'] == '(↑1)'
        await p.save_record('race', 'Race', 'PC', p.PlayerStatsData(1, 100, '青铜', 4, prestige=0))
        same = await asyncio.gather(*(p._compare_and_save(
            'race', 'PC', 'Race', 1, 120, '青铜', 4, '大逃杀分数: 120', prestige=0) for _ in range(2)))
        assert [r[1] for r in same] == [20, 0], same

        # An older request completing late cannot roll back the comparison baseline.
        observed = datetime.now(timezone.utc)
        await p._compare_and_save('late', 'PC', 'Late', 1, 120, '青铜', 4,
                                 '大逃杀分数: 120', observed_at=observed)
        late = await p._compare_and_save('late', 'PC', 'Late', 1, 110, '青铜', 4,
                                        '大逃杀分数: 110', observed_at=observed - timedelta(seconds=1))
        assert late == ({}, None, '大逃杀分数: 110'), late
        assert (await p.get_latest_record('late', 'PC')).rank_score == 120

        class Frontend:
            def __init__(self): self.sent = []
            async def send_message(self, **kwargs):
                self.sent.append(str(kwargs['content']))
                return str(len(self.sent))
        adapter = nonebot.get_adapter(Adapter)
        adapter._frontend = Frontend()
        bot = Bot(adapter, Robot('testbot'))
        adapter.bot_connect(bot)
        async def command():
            adapter._frontend.sent.clear()
            event = MessageEvent(time=datetime.now(), self_id=bot.self_id,
                user=User('tester'), channel=Channel('test', 'Test'),
                message_id='test-message', message=Message('/apex Test'))
            await bot.handle_event(event)
            return '\n'.join(adapter._frontend.sent)
        async with p.get_session() as session:
            before = await session.scalar(select(func.count()).select_from(p.PlayerStats))
        with patch.object(p, '_fetch', AsyncMock(return_value={'global': None})):
            assert '玩家数据不完整' in await command()
        async with p.get_session() as session:
            after = await session.scalar(select(func.count()).select_from(p.PlayerStats))
        assert before == after, 'Malformed responses must not create history records'
        data = {'global': {'uid': 'command', 'name': 'Test', 'platform': 'PC', 'level': 1,
            'levelPrestige': 0, 'rank': {'rankName': 'Gold', 'rankDiv': 4, 'rankScore': 100}}}
        with patch.object(p, '_fetch', AsyncMock(return_value=data)), patch.object(p.config, 'apex_only_text', True):
            assert '名称: Test' in await command()
            data['global']['level'] = 2
            data['global']['rank']['rankScore'] = 120
            reply = await command()
            assert '(↑1)' in reply and '(↑20)' in reply, reply
        with patch.object(p, '_fetch', AsyncMock(return_value=data)), patch.object(p, 'render_player_card', AsyncMock(return_value=b'png')):
            reply = await command()
            assert '名称: Test' in reply and '[image]' not in reply
        adapter.bot_disconnect(bot)
        print('PASS legacy migration, prestige, concurrent ORM comparisons, Console commands and text fallback')
    finally:
        await driver._lifespan.shutdown()
        # The subprocess owns these engines; release SQLite handles before cleanup.
        import nonebot_plugin_orm as orm
        for engine in orm._engines.values():
            await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
