from pydantic import BaseModel, Extra

class Config(BaseModel, extra=Extra.ignore):
    apex_api_key: str = '173fd0ee53fb32d4c7063eb5bc700c9e'
    apex_api_url: str = 'https://api.mozambiquehe.re/'