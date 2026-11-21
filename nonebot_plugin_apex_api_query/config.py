from nonebot.plugin import get_plugin_config
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    apex_api_key: str = Field(default="", validate_default=True)
    apex_api_url: str = "https://api.apexlegendsstatus.com"
    apex_only_text: bool = Field(default=False)

    @field_validator("apex_api_key", mode="after")
    @classmethod
    def strip_api_key(cls, v: str) -> str:
        return v.strip()


config = get_plugin_config(Config)
