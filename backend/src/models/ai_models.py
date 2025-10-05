from pydantic import BaseModel
from typing import Optional

class AskRequest(BaseModel):
    query: str
    portfolio: Optional[dict] = None

class AskResponse(BaseModel):
    response_text: str
