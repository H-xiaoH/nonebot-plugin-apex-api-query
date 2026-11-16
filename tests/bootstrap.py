"""Load the real plugin with isolated local storage and no external bots."""
import atexit
import os
import tempfile
from pathlib import Path

import nonebot
from nonebot.adapters.console import Adapter

_runtime = tempfile.TemporaryDirectory(prefix='apex-tests-')
atexit.register(_runtime.cleanup)
ROOT = Path(_runtime.name)
DEFAULT_DATABASE = bool(os.environ.get('APEX_TEST_DEFAULT_DB'))
DATABASE = ROOT / 'data' / 'nonebot_plugin_orm' / 'db.sqlite3' if DEFAULT_DATABASE else ROOT / 'stats.sqlite3'
nonebot.init(
    driver='~none', apex_api_key='test-api-key', telegram_bots=[],
    console_headless_mode=True, log_level='ERROR',
    localstore_data_dir=ROOT / 'data', localstore_cache_dir=ROOT / 'cache',
    localstore_config_dir=ROOT / 'config',
    sqlalchemy_database_url='' if DEFAULT_DATABASE else f'sqlite+aiosqlite:///{DATABASE}',
    render={'provider': 'playwright', 'startup': 'off', 'resources': {
        'local_access': {'allowed_paths': [str(Path(__file__).parents[1] / 'nonebot_plugin_apex_api_query')]}}},
)
nonebot.get_driver().register_adapter(Adapter)
plugin = nonebot.load_plugin('nonebot_plugin_apex_api_query')
assert plugin is not None, 'The real plugin must load successfully'
p = plugin.module
