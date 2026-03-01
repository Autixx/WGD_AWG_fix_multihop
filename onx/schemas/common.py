from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ONXBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(ONXBaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
