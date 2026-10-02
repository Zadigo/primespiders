from pydantic import BaseModel, Field, model_validator


class GooglePlaceModel(BaseModel):
    reference: str | None = Field(
        default=None,
        description="The reference of the Google Place"
    )
    url: str | None = Field(
        default=None,
        description="The URL of the Google Place"
    )
    name: str | None = Field(
        default=None,
        description="The name of the Google Place"
    )

    def __hash__(self):
        return hash(self.reference)

    @model_validator(mode='before')
    @classmethod
    def validate_data(cls, value: dict):
        if isinstance(value, dict):
            value['rating'] = float(value.get('rating', 1))
        return value


class GoogleReviewModel(BaseModel):
    pass
