import unidecode
from pydantic import Field, model_validator

from primespiders.components.models import BaseStudyModel


class PublicationModel(BaseStudyModel):
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
    summary: str | None = Field(
        default=None,
        description="The summary of the publication"
    )

    @model_validator(mode='before')
    @classmethod
    def validate_slug(cls, values):
        if values.get('title'):
            str_title = values['title'].lower().replace("'", "").replace(' ', '-')
            values['slug'] = unidecode.unidecode(str_title)
        return values
