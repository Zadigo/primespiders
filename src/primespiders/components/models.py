from pydantic import BaseModel, Field, field_validator, model_validator

from primespiders.utils.slug import create_slug


class BaseStudyModel(BaseModel):
    year: int | None = Field(
        default=None,
        description="The year of the EU study"
    )
    date: str | None = Field(
        default=None,
        description="The date of the publication"
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
    slug: str | None = Field(
        default=None,
        description="The slug of the publication"
    )

    @field_validator('year')
    @classmethod
    def validate_year(cls, value):
        if value is not None and (value < 1900 or value > 2100):
            raise ValueError("Year must be between 1900 and 2100")
        return value

    @field_validator('pdf_url', mode='before')
    @classmethod
    def validate_pdf_url(cls, value):
        if (
            value is not None and 
            not value.startswith("http") and
            not value.endswith(".pdf")
        ):
            raise ValueError("PDF URL must start with 'http' and end with '.pdf'")
        return value

    @model_validator(mode='before')
    @classmethod
    def validate_slug(cls, values: dict):
        if values.get('title'):
            values['slug'] = create_slug(values['title'])

        # date = values.get('date')
        # year = values.get('year')
        # if date is not None and year is None:
        #     values['year'] = int(date.split('-')[0])

        return values
