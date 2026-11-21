import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from contextlib import nullcontext

import httpx

from tests.bootstrap import p
from nonebot_plugin_apex_api_query.config import Config


class DataPipelineTests(unittest.IsolatedAsyncioTestCase):
    def test_missing_and_blank_keys_allow_loading(self):
        for values in ({}, {'apex_api_key': ''}, {'apex_api_key': '  '}):
            self.assertEqual(Config(**values).apex_api_key, '')
        self.assertEqual(Config(apex_api_key=' valid ').apex_api_key, 'valid')

    async def test_fetch_rejects_non_objects_and_invalid_json(self):
        for response in (httpx.Response(200, json=[]), httpx.Response(200, json=None), httpx.Response(200, text='invalid')):
            with patch.object(p, 'query_apex_api', AsyncMock(return_value=response)):
                with self.assertRaises(p.ApexAPIError):
                    await p._fetch('bridge')

    async def test_incomplete_player_fields_are_not_zero_filled(self):
        valid = {'uid': '1', 'level': 0, 'rank': {'rankName': 'Unranked', 'rankScore': 0}}
        for global_data in (None, {}, {**valid, 'level': None}, {**valid, 'rank': {}},
                            {**valid, 'level': True}, {**valid, 'rank': {'rankName': [], 'rankScore': 0}}):
            with patch.object(p, '_fetch', AsyncMock(return_value={'global': global_data})):
                with self.assertRaises(p.ApexAPIError):
                    await p.get_player_stats('Test')
        with patch.object(p, '_fetch', AsyncMock(return_value={'global': valid})):
            _, data = await p.get_player_stats('Test')
            self.assertEqual((data['level'], data['rank_score']), (0, 0))
        with patch.object(p, '_fetch', AsyncMock(return_value={'global': valid, 'realtime': {'selectedLegend': []}})):
            _, data = await p.get_player_stats('Test')
            self.assertIsNone(data['selected_legend'])

    async def test_uid_query_is_explicit_and_checks_response_identity(self):
        data = {'global': {'uid': '1001', 'level': 1, 'rank': {'rankName': 'Unranked', 'rankScore': 0}}}
        with patch.object(p, '_fetch', AsyncMock(return_value=data)) as fetch:
            _, raw = await p.get_player_stats('Cached name', 'pc', uid='0001001')
            fetch.assert_awaited_once_with('bridge', {'platform': 'PC', 'uid': '1001'})
            self.assertEqual(raw['name'], 'Cached name')
            with self.assertRaises(p.ApexAPIError):
                await p.get_player_stats('Cached name', uid='1002')
        for uid in ('', '0', 'not-a-uid', '１２３', '9' * 33):
            with self.subTest(uid=uid), patch.object(p, '_fetch', AsyncMock()) as fetch:
                with self.assertRaises(p.ApexAPIError):
                    await p.get_player_stats('Test', uid=uid)
                fetch.assert_not_awaited()

    async def test_each_public_cache_coalesces_concurrent_calls_and_expires(self):
        cases = [
            (p.get_map_rotation_data, '_map_rotation_cache', {'battle_royale': {'current': {'map': 'Test'}}}),
            (p.get_server_status_data, '_server_status_cache', {'Origin_login': {'Asia': {'Status': 'UP', 'ResponseTime': 0}}}),
            (p.get_predator_data, '_predator_cache', {'RP': {'PC': {'val': 0, 'totalMastersAndPreds': 0}}}),
        ]
        for get_data, name, response in cases:
            with self.subTest(cache=name):
                async def fetch(*args):
                    await asyncio.sleep(0.01)
                    return response
                cache = p.AsyncTTLCache(ttl=60)
                with patch.object(p, name, cache), patch.object(p, '_fetch', AsyncMock(side_effect=fetch)) as request:
                    values = await asyncio.gather(*(get_data() for _ in range(8)))
                    self.assertTrue(all(value == values[0] for value in values))
                    request.assert_awaited_once()
                    await get_data()
                    request.assert_awaited_once()
                    cache._ttl = -1
                    await get_data()
                    self.assertEqual(request.await_count, 2)

    async def test_bad_response_is_not_cached_or_fabricated_as_zero(self):
        with patch.object(p, '_predator_cache', p.AsyncTTLCache(ttl=60)), patch.object(p, '_fetch', AsyncMock(side_effect=[{}, {'RP': {'PC': {'val': 100}}}])) as request:
            text, data = await p.get_predator()
            self.assertIn('数据不完整', text)
            self.assertEqual(data, {})
            text, data = await p.get_predator()
            self.assertEqual(data['PC']['val'], 100)
            self.assertNotIn('PS4', data)
            self.assertIn('顶尖猎杀者人数: 未知', text)
            self.assertEqual(request.await_count, 2)

    def test_prestige_cycle_and_legacy_rows(self):
        previous = p.PlayerStatsData(500, 100, '青铜', 4, prestige=1)
        current = p.PlayerStatsData(1, 100, '青铜', 4, prestige=2)
        self.assertEqual(p.format_comparison(current, previous)['等级'], '(↑1)')
        legacy = p.PlayerStatsData(500, 100, '青铜', 4)
        self.assertNotIn('等级', p.format_comparison(current, legacy))

    async def test_artwork_has_a_total_deadline_and_cancels_download(self):
        cancelled = asyncio.Event()
        async def slow_stream(url):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        with patch.object(p, '_ARTWORK_TIMEOUT', 0.01), patch.object(p, '_load_image_uri', slow_stream):
            self.assertEqual(await asyncio.wait_for(p._image_uri('https://example.com/image'), 1), '')
            self.assertTrue(cancelled.is_set())

    async def test_404_artwork_is_cached_without_network_access(self):
        original_client = httpx.AsyncClient
        calls = 0
        async def handle(request):
            nonlocal calls
            calls += 1
            return httpx.Response(404)
        def client(**kwargs):
            return original_client(transport=httpx.MockTransport(handle), **kwargs)
        with patch.object(p, '_missing_image_cache', p.AsyncTTLCache(ttl=3600)), patch.object(p.httpx, 'AsyncClient', client):
            for _ in range(2):
                self.assertEqual(await p._image_uri('https://example.com/missing.png'), '')
            self.assertEqual(calls, 1)

    async def test_concurrent_failures_share_request_and_allow_retry(self):
        cache = p.AsyncTTLCache()
        async def fail():
            await asyncio.sleep(0.01)
            raise p.ApexAPIError('offline')
        fetch = AsyncMock(side_effect=fail)
        results = await asyncio.gather(*(cache.get_or_fetch('key', fetch) for _ in range(8)), return_exceptions=True)
        self.assertTrue(all(isinstance(result, p.ApexAPIError) for result in results))
        fetch.assert_awaited_once()
        with self.assertRaises(p.ApexAPIError):
            await cache.get_or_fetch('key', fetch)
        self.assertEqual(fetch.await_count, 2)

    async def test_cancelling_one_waiter_keeps_shared_request(self):
        cache = p.AsyncTTLCache()
        started, release = asyncio.Event(), asyncio.Event()
        async def fetch():
            started.set()
            await release.wait()
            return 'result'
        first = asyncio.create_task(cache.get_or_fetch('key', fetch))
        await started.wait()
        second = asyncio.create_task(cache.get_or_fetch('key', fetch))
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        release.set()
        self.assertEqual(await second, 'result')
        self.assertEqual(await cache.get('key'), 'result')

    def test_models_compile_for_mysql(self):
        from sqlalchemy.schema import CreateTable, CreateIndex
        from sqlalchemy.dialects.mysql import dialect
        from nonebot_plugin_apex_api_query.models import PlayerBinding, PlayerStats
        for model in (PlayerBinding, PlayerStats):
            self.assertIn('CREATE TABLE', str(CreateTable(model.__table__).compile(dialect=dialect())))
            for index in model.__table__.indexes:
                self.assertIn('CREATE INDEX', str(CreateIndex(index).compile(dialect=dialect())))

    async def test_key_startup_missing_invalid_valid_and_temporary_errors(self):
        for key, response, expected in (
            ('', None, False),
            ('test-key', httpx.Response(403, text='secret-canary'), False),
            ('test-key', httpx.Response(200, json={'Origin_login': {}}), True),
            ('test-key', httpx.Response(429, text='secret-canary'), None),
            ('test-key', httpx.Response(500, text='secret-canary'), None),
        ):
            with self.subTest(status=response.status_code if response else 'missing'), \
                    patch.object(p, '_api_key_available', None), \
                    patch.object(p.config, 'apex_api_key', key), \
                    patch.object(p, 'query_apex_api', AsyncMock(return_value=response)) as request:
                with self.assertLogs(p.logger, level='WARNING') if expected is not True else nullcontext() as logs:
                    await p.check_api_key()
                self.assertIs(p._api_key_available, expected)
                if not key:
                    request.assert_not_awaited()
                if logs:
                    self.assertNotIn('secret-canary', '\n'.join(logs.output))

    async def test_network_failure_does_not_mark_key_invalid(self):
        with patch.object(p, '_api_key_available', None), patch.object(p, 'query_apex_api',
                AsyncMock(side_effect=httpx.ConnectError('secret-canary'))):
            with self.assertLogs(p.logger, level='WARNING') as logs:
                await p.check_api_key()
            self.assertIsNone(p._api_key_available)
            self.assertNotIn('secret-canary', '\n'.join(logs.output))

    async def test_auth_failure_has_safe_chat_error(self):
        for status in (401, 403):
            with patch.object(p, '_api_key_available', None), patch.object(p, 'query_apex_api',
                    AsyncMock(return_value=httpx.Response(status, text='secret-canary'))):
                with self.assertRaisesRegex(p.ApexAPIError, '^API密钥不可用$'):
                    await p._fetch('bridge')
                self.assertFalse(p._api_key_available)

    async def test_key_is_sent_in_header_not_url(self):
        original_client = httpx.AsyncClient
        async def handle(request):
            self.assertEqual(request.headers['Authorization'], 'test-api-key')
            self.assertNotIn('auth', request.url.params)
            return httpx.Response(200, json={})
        def client(**kwargs):
            return original_client(transport=httpx.MockTransport(handle), **kwargs)
        with patch.object(p.httpx, 'AsyncClient', client):
            await p.query_apex_api('servers')
