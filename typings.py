from collections.abc import AsyncGenerator, Generator, Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from primespiders.base import BaseSpider
    from primespiders.utils.urls import URL


class EcommerceMixinProtocol(Protocol):
    start_url: URL | None = None


type TypeURL = URL

type TypeUrls = Sequence[URL] | Generator[URL] | AsyncGenerator[URL]

type TypeBaseSpider = BaseSpider
