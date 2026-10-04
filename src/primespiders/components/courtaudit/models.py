import unidecode
from pydantic import BaseModel, Field, model_validator


class PublicationModel(BaseModel):
    title: str | None = Field(
        default=None,
        description="The title of the publication"
    )
    theme: str | None = Field(
        default=None,
        description="The theme of the publication"
    )
    theme_url: str | None = Field(
        default=None,
        description="The URL of the theme of the publication"
    )
    url: str | None = Field(
        default=None,
        description="The URL of the publication"
    )
    pdf_url: str | None = Field(
        default=None,
        description="The URL of the PDF of the publication"
    )
    date: str | None = Field(
        default=None,
        description="The date of the publication"
    )
    summary: str | None = Field(
        default=None,
        description="The summary of the publication"
    )
    slug: str | None = Field(
        default=None,
        description="The slug of the publication"
    )

    @model_validator(mode='before')
    @classmethod
    def validate_slug(cls, values):
        if values.get('title'):
            str_title = values['title'].lower().replace("'", "").replace(' ', '-')
            values['slug'] = unidecode.unidecode(str_title)
        return values
