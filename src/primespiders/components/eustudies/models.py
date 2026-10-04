from pydantic import Field

from primespiders.components.models import BaseStudyModel


class EuStudyModel(BaseStudyModel):
    study_type: str | None = Field(
        default=None,
        description="The type of the EU study"
    )
