"""插件配置模块。

通过 NoneBot 的 get_plugin_config 从 .env 文件中加载配置，
使用 Pydantic 进行字段校验，启动时自动验证 API Key 是否已设置。
"""

from nonebot.plugin import get_plugin_config
from pydantic import BaseModel, Field, field_validator


class MissingAPIKeyError(ValueError):
    """API 密钥未配置时抛出的异常。"""


class Config(BaseModel):
    """插件配置，对应 .env 中的环境变量。"""

    # Field(default="") 允许未配置时使用空字符串默认值，
    # 由下方的 @field_validator 在启动时拦截并报错
    apex_api_key: str = Field(default="")
    """Your API Key from https://portal.apexlegendsapi.com/"""

    apex_api_url: str = "https://api.mozambiquehe.re"
    """Apex Legends API base URL"""

    @field_validator("apex_api_key", mode="after")
    @classmethod
    def api_key_must_not_be_empty(cls, v: str) -> str:
        """启动时校验 API Key 非空，未配置则阻止插件加载。"""
        if not v:
            raise MissingAPIKeyError
        return v


# 全局单例，供其他模块通过 from .config import config 直接使用
config = get_plugin_config(Config)
