import logging

from pydantic import BaseModel
from nonebot.plugin import get_plugin_config

logger = logging.getLogger(__name__)


class Config(BaseModel):
    """Plugin Config Here"""
    apex_api_key: str = ""
    """Your API Key from https://portal.apexlegendsapi.com/"""


config = get_plugin_config(Config)

if not config.apex_api_key:
    logger.warning(
        "APEX_API_KEY 未配置，所有 API 请求将失败。"
        "请在 .env 文件中添加 APEX_API_KEY=你的密钥"
    )
