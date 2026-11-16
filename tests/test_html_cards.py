"""Card content and async rendering regressions without API/browser access."""
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tests.bootstrap import p

ROOT = Path(__file__).parents[1] / 'nonebot_plugin_apex_api_query'


class HtmlCardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=select_autoescape())
        self.env.filters['convert'] = p.convert
        self.card = AsyncMock(return_value=b'png')
        patcher = patch.multiple(p, _render_card=self.card, _fetch=p._fetch, config=p.config,
            _LEGEND_BACKGROUNDS={'Alter': 'https://example.com/alter.png'},
            _image_uri=AsyncMock(return_value='data:image/png;base64,test'))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.scope = p.__dict__

    def render(self, name, **values):
        return self.env.get_template(name + '.html').render(title='Test', font='test-font', **values)

    async def test_zero_score_changes_and_html_escaping(self):
        html = self.render('player', player={'name': '<script>bad()</script>', 'rank_score': 0, 'level': 0},
                           changes={'等级': '(↑1)', '大逃杀段位': '(黄金 3)'}, score_diff=-20)
        self.assertIn('0 分', html)
        self.assertIn('(↑1)', html)
        self.assertIn('黄金 3', html)
        self.assertIn('-20', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    async def test_server_status_is_text_not_only_color(self):
        html = self.render('server', sections=[{'section_name': '测试', 'rows': [
            {'name': 'Asia', 'status': 'UP', 'response_time': 0},
            {'name': 'Other', 'status': 'DOWN', 'response_time': -1}]}])
        self.assertIn('在线', html)
        self.assertIn('离线', html)
        self.assertIn('0ms', html)
        self.assertNotIn('-1ms', html)

    async def test_player_artwork_does_not_mutate_query_data(self):
        player = {'name': 'Test', 'rank_img': 'https://example.com/rank.png', 'legend_banner': 'https://example.com/banner.jpg',
                  'avatar': 'https://example.com/avatar.jpg'}
        self.assertEqual(await self.scope['render_player_card'](player), b'png')
        self.assertEqual(player['rank_img'], 'https://example.com/rank.png')
        self.assertTrue(self.card.call_args.kwargs['player']['rank_img'].startswith('data:'))
        self.assertEqual(player['legend_banner'], 'https://example.com/banner.jpg')
        self.assertTrue(self.card.call_args.kwargs['player']['legend_banner'].startswith('data:'))
        for key in ('avatar',):
            self.assertTrue(player[key].startswith('https://'))
            self.assertTrue(self.card.call_args.kwargs['player'][key].startswith('data:'))

    async def test_optional_player_details_in_text_and_card(self):
        data = {'global': {'uid': '1', 'level': 0, 'levelPrestige': 0, 'battlepass': {'level': 0}, 'rank': {
            'rankScore': 0, 'rankName': 'Unranked', 'rankedSeason': 'br_ranked_s31_s1', 'ALStopPercentGlobal': 0}},
            'legends': {'selected': {'LegendName': 'Wraith', 'gameInfo': {'skin': '<Test skin>', 'skinRarity': 'Legendary'},
                'ImgAssets': {'banner': 'https://example.com/wraith.jpg', 'icon': 'https://example.com/wraith.png'}, 'data': [
                    {'name': 'BR Kills', 'key': 'specialEvent_kills', 'value': 0},
                    {'name': 'Unknown', 'value': -1}, {'name': 'Missing', 'value': None}]}}}
        self.scope['_fetch'] = AsyncMock(return_value=data)
        text, raw = await self.scope['get_player_stats']('Test')
        self.assertIn('转生等级: 0', text)
        self.assertIn('战斗通行证等级: 0', text)
        self.assertIn('S31 · 第 1 赛段', text)
        self.assertIn('前 0%', text)
        self.assertIn('恶灵追踪器 · 大逃杀击杀: 0', text)
        self.assertIn('不代表完整生涯统计', text)
        self.assertEqual(raw['trackers'], [{'name': '大逃杀击杀', 'value': 0}])
        html = self.render('player', player=raw, changes={}, score_diff=None)
        self.assertIn('已装备追踪器', html)
        self.assertIn('&lt;Test skin&gt;', html)
        self.assertIn('class="player-backdrop"', html)
        self.assertEqual(raw['legend_skin_rarity'], 'Legendary')
        self.assertIn('color:#ffd166', html)

    async def test_missing_details_and_unavailable_percentile_are_hidden(self):
        self.scope['_fetch'] = AsyncMock(return_value={'global': {'uid': '1', 'level': 0, 'rank': {'rankName': 'Unranked', 'rankScore': 0, 'ALStopPercentGlobal': 'No game this split'},
            'battlepass': None}, 'legends': {'selected': None}})
        text, raw = await self.scope['get_player_stats']('Test')
        for label in ['转生等级:', '战斗通行证等级:', 'ALS 收录玩家排名:', '当前传奇皮肤:']:
            self.assertNotIn(label, text)
        html = self.render('player', player=raw, changes={}, score_diff=None)
        self.assertNotIn('已装备追踪器', html)
        self.assertNotIn('class="player-backdrop"', html)

    async def test_failed_background_download_keeps_card_renderable(self):
        self.scope['_image_uri'] = AsyncMock(return_value='')
        await self.scope['render_player_card']({'name': 'Test', 'legend_banner': 'https://example.com/banner.jpg'})
        raw = self.card.call_args.kwargs['player']
        self.assertEqual(raw['legend_banner'], '')
        html = self.render('player', player=raw, changes={}, score_diff=None)
        self.assertIn('no-banner', html)
        self.assertIn('Test', html)

    async def test_blank_name_falls_back_in_text_and_image_data(self):
        for name in ('', '   ', None):
            self.scope['_fetch'] = AsyncMock(return_value={'global': {'uid': '1', 'level': 0, 'name': name,
                'rank': {'rankName': 'Master', 'rankDiv': 1, 'rankScore': 0}}})
            text, raw = await self.scope['get_player_stats']('chuwen111')
            self.assertIn('名称: chuwen111', text)
            self.assertEqual(raw['name'], 'chuwen111')
            self.assertIn('大逃杀段位: 大师', text.splitlines())
            await self.scope['render_player_card'](raw)
            self.assertEqual(self.card.call_args.kwargs['player']['rank_display'], '大师')

    async def test_rank_divisions_and_historical_placeholders(self):
        rank = self.scope['_format_rank']
        for name in ('Master', '大师', 'Apex Predator', 'Apex 猎杀者', 'Unranked', '无段位'):
            self.assertEqual(rank(name, 1), name)
        self.assertEqual(rank('白金', 3), '白金 3')
        previous = SimpleNamespace(prestige=0, level=1, rank_score=16000, rank_name='大师', rank_div=1)
        current = SimpleNamespace(prestige=0, level=1, rank_score=16000, rank_name='大师', rank_div=2)
        self.assertEqual(self.scope['format_comparison'](current, previous), {})

    async def test_official_banner_only_used_when_primary_missing(self):
        async def fetch(url):
            return 'data:fallback' if url == 'https://example.com/alter.png' else ''
        self.scope['_image_uri'] = AsyncMock(side_effect=fetch)
        await self.scope['render_player_card']({'legend_key': 'Alter', 'legend_banner': 'https://example.com/missing.jpg'})
        self.assertEqual(self.card.call_args.kwargs['player']['legend_banner'], 'data:fallback')
        self.scope['_image_uri'] = AsyncMock(return_value='data:primary')
        await self.scope['render_player_card']({'legend_key': 'Alter', 'legend_banner': 'https://example.com/primary.jpg'})
        self.assertEqual(self.card.call_args.kwargs['player']['legend_banner'], 'data:primary')
        self.assertNotIn(('https://example.com/alter.png',), [call.args for call in self.scope['_image_uri'].call_args_list])

    async def test_map_progress_bounded_and_input_preserved(self):
        data = {'ranked': {'current': {'map': 'Test', 'asset': '', 'remainingSecs': 10, 'DurationInSecs': 0}}}
        await self.scope['render_map_card'](data)
        mode = self.card.call_args.kwargs['modes'][0]
        self.assertEqual(mode['progress'], 100)
        self.assertEqual(data['ranked']['current']['asset'], '')

    async def test_async_render_failure_returns_full_text(self):
        class Finished(Exception):
            pass
        matcher = type('Matcher', (), {'finish': AsyncMock(side_effect=Finished)})
        self.scope['config'] = type('Config', (), {'apex_only_text': False})
        render = AsyncMock(side_effect=RuntimeError('browser failed'))
        with self.assertRaises(Finished):
            await self.scope['_render_or_fallback'](matcher, AsyncMock(return_value=('full text', {'ok': True})), render)
        matcher.finish.assert_awaited_once_with('full text')
