from pydantic import BaseModel


class SecurityRequest(BaseModel):
    api_key: str
    tool: str
    arguments: dict
    resource: str | None = None
    trigger_message: str | None = None