from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ProductModel(BaseModel):
    title: str
    unit_price: float
    sale_price: float | None = None
    available_sizes: Sequence[str] = Field(default_factory=list)
    color: str
    reference: str
    product_images: Sequence[str] = Field(default_factory=list)
    sizes: Sequence[str] = Field(default_factory=list)
    url: str

    @model_validator(mode='before')
    @classmethod
    def validate_data(cls, data: dict[str, Any]):
        if isinstance(data, dict):
            for key, value in data.items():
                if 'price' in key:
                    try:
                        data[key] = float(value)
                    except (TypeError, ValueError):
                        data[key] = None
                    else:
                        continue

                if 'size' in key:
                    if isinstance(value, list):
                        data[key] = [str(v) for v in value]
                    else:
                        data[key] = []
        return data
