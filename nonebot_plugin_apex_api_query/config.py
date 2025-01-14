from pydantic import BaseModel
from nonebot.plugin import get_plugin_config

class Config(BaseModel):
    """Plugin Config Here"""
    apex_api_key: str = ""
    """Your API Key from https://portal.apexlegendsapi.com/"""

config = get_plugin_config(Config)
