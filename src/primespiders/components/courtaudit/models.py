from pydantic import BaseModel, Field


class PublicationModel(BaseModel):
    title: str | None = Field(
        default=None,
        description="The title of the publication"
    )
    url: str | None = Field(
        default=None,
        description="The URL of the publication"
    )
    date: str | None = Field(
        default=None,
        description="The date of the publication"
    )
    summary: str | None = Field(
        default=None,
        description="The summary of the publication"
    )
