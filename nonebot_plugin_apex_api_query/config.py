from pydantic import BaseModel
from typing import Optional

class Config(BaseModel):
    """Plugin Config Here"""
    APEX_API_KEY: Optional[str] = None
