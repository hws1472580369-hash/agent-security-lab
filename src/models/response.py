from pydantic import BaseModel


class SecurityResponse(BaseModel):
    allowed: bool
    decision: str
    error_code: str | None = None
    reason: str