from pydantic import BaseModel, Extra

class Config(BaseModel, extra=Extra.ignore):
    apex_api_key: str = 'YOUR_APEX_API_KEY'
    apex_api_url: str = 'https://api.mozambiquehe.re/'