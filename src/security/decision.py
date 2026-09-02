from pydantic import BaseModel


class SecurityDecision(BaseModel):
    allowed: bool
    error_code: str | None = None
    reason: str | None = None