from nonebot.plugin import get_plugin_config
from pydantic import BaseModel, Field, field_validator


class MissingAPIKeyError(ValueError):
    """未配置 Apex API Key 时抛出的异常，阻止插件加载。"""


class Config(BaseModel):
    apex_api_key: str = Field(default="")
    apex_api_url: str = "https://api.mozambiquehe.re"

    @field_validator("apex_api_key", mode="after")
    @classmethod
    def api_key_must_not_be_empty(cls, v: str) -> str:
        """校验 apex_api_key 非空，空值时抛出 MissingAPIKeyError。

        Args:
            v: 配置中的 apex_api_key 值。

        Returns:
            校验通过的原值。

        Raises:
            MissingAPIKeyError: API Key 为空时抛出。
        """
        if not v:
            raise MissingAPIKeyError
        return v


config = get_plugin_config(Config)
