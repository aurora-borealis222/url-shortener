from datetime import datetime
from pydantic import BaseModel, Field

class LinkRequest(BaseModel):
    original_url: str
    custom_alias: str = None

class LinkResponse(BaseModel):
    original_url: str
    short_code: str

class LinkStatsResponse(BaseModel):
    creation_date: datetime
    clicks_count: int
    last_usage_at: datetime = None

