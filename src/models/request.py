from pydantic import BaseModel


class SecurityRequest(BaseModel):
    api_key: str
    tool: str
    arguments:dict
    resource:str | None = None

