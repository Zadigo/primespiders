from pydantic import Field

from primespiders.components.models import BaseStudyModel


class IfopStudyModel(BaseStudyModel):
    abstract_title: str | None = Field(
        None,
        description="The title of the abstract of the EU study"
    )
    abstract_text: str | None = Field(
        None,
        description="The text of the abstract of the EU study"
    )
