from nonebot.plugin import get_plugin_config
from pydantic import BaseModel, Field, field_validator


class MissingAPIKeyError(ValueError):
    pass


class Config(BaseModel):
    apex_api_key: str = Field(default="")
    apex_api_url: str = "https://api.apexlegendsstatus.com"
    apex_only_text: bool = Field(default=False)

    @field_validator("apex_api_key", mode="after")
    @classmethod
    def api_key_must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise MissingAPIKeyError
        return v


config = get_plugin_config(Config)
