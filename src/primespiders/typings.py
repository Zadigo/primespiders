from abc import abstractmethod
from collections.abc import Callable, Generator, Sequence
from typing import TYPE_CHECKING, Literal, Protocol

import playwright
from redis import Redis

if TYPE_CHECKING:
    from primespiders.base import BaseSpider
    from primespiders.observer import SignalsContainer
    from primespiders.utils.urls import URL
    

class EcommerceMixinProtocol(Protocol):
    start_url: URL | None = None
    storage_key_template: Literal["primespiders:{job_uuid}{suffix}"]
    default_timeout: Literal[30000] = 30000
    url_filters: Sequence[Callable[[URL], bool]] = ()
    page: playwright.sync_api.Page
    _accepted_domain: URL | None = None
    redis_client: Redis | None = None
    job_uuid: str
    urls_to_visit_key: str 
    visited_urls_key: str
    seen_urls_key: str
    signals: SignalsContainer | None = None

    @property
    def get_url_filters(self) -> Sequence[Callable[[URL], bool]]: ...

    @property
    def urls_to_visit(self) -> Sequence[URL]: ...

    @staticmethod
    async def url_to_str(urls: TypeUrls) -> Sequence[str]: ...
    
    @abstractmethod
    async def run(self): ...


type TypeURL = URL

type TypeUrls = Sequence[URL] | Generator[URL]

type TypeBaseSpider = BaseSpider

type TypeSignalContainer = SignalsContainer
