from pydantic import BaseModel, Field


class EuStudyModel(BaseModel):
    study_type: str | None = Field(
        default=None,
        description="The type of the EU study"
    )
    year: int | None = Field(
        default=None,
        description="The year of the EU study"
    )
    title: str | None = Field(
        default=None,
        description="The title of the EU study"
    )
    abstract: str | None = Field(
        default=None,
        description="The abstract of the EU study"
    )
    pdf_url: str | None = Field(
        default=None,
        description="The URL of the PDF of the EU study"
    )
