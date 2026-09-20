import pydantic
from pydantic import Field

from src.primespiders.observer import PerformanceModel


class WsReceiveMessage(pydantic.BaseModel):
    action: str | None = Field(default=None)
    message: str | None = Field(default=None)


class UrlsToVisitModel(pydantic.BaseModel):
   url: str = Field(default="")


class ListSpidersModel(pydantic.BaseModel):
    name: str | None = Field(default=None)
    performance: PerformanceModel | None = Field(default=None)
