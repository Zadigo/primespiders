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
    review_id: str | None = Field(
        default=None,
        description="The ID of the Google Review"
    )
    author_name: str | None = Field(
        default=None,
        description="The name of the author of the Google Review"
    )
    rating: float | None = Field(
        default=None,
        description="The rating given in the Google Review",
        ge=0.0, le=5.0
    )
    text: str | None = Field(
        default=None,
        description="The text content of the Google Review"
    )



class GoogleAdvancedPlaceModel(GooglePlaceModel):
    reviews: list[GoogleReviewModel] | None = Field(
        default_factory=list,
        description="The list of reviews for the Google Place"
    )
    rating: float | None = Field(
        default=None,
        description="The rating of the Google Place",
        ge=0.0, le=5.0
    )
    number_of_reviews: int | None = Field(
        default=0,
        description="The number of reviews for the Google Place",
        ge=0
    )
    address: str | None = Field(
        default=None,
        description="The address of the Google Place"
    )
    website: str | None = Field(
        default=None,
        description="The website of the Google Place"
    )
    phone_number: str | None = Field(
        default=None,
        description="The phone number of the Google Place"
    )
    category: str | None = Field(
        default=None,
        description="The category of the Google Place"
    )
