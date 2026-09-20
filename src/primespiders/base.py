import asyncio
import io
import os
import pathlib
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable, Sequence
from typing import Any
from uuid import uuid4

import aiofiles
import pandas
import pydantic
from playwright.async_api import Page

from src.primespiders.observer import (
    HistoryObserver,
    PerformanceObserver,
    SignalsContainer,
)
from src.primespiders.typings import EcommerceMixinProtocol, TypeUrls
from src.primespiders.utils import logger
from src.primespiders.utils.clients import get_redis
from src.primespiders.utils.operators import BaseCondition
from src.primespiders.utils.urls import URL


class EcommerceMixin:
    items_storage_key: str | None = None

    async def get_products[T = pydantic.BaseModel](self: EcommerceMixinProtocol, model: T) -> Sequence[T]:
        if self.redis_client is None or self.items_storage_key is None:
            return []

        values = self.redis_client.lrange(self.items_storage_key, 0, -1)
        return [model.model_validate_json(v) for v in values]

    async def save_product[T = pydantic.BaseModel](self: EcommerceMixinProtocol, model: T) -> None:
        if self.signals is not None:
            self.items_storage_key = await self.signals.save_item(model)

    def check_is_product_page(self: EcommerceMixinProtocol, url: URL) -> bool:
        """Implement this method to check if the given URL corresponds to a product page."""
        return False

    def check_is_category_page(self: EcommerceMixinProtocol, url: URL) -> bool:
        """Implement this method to check if the given URL corresponds to a category page."""
        return False


class BaseSpider(ABC):
    """Base class for all spiders.

    Args:
        page (Page): The Playwright page instance for the spider.

    Attributes:
        start_url (URL | None): The starting URL for the spider.
        storage_key_template (str): Template for Redis storage keys.
        default_timeout (int): Default timeout for requests.
        url_filters (Sequence[Callable[[URL], bool]]): Filters to apply to URLs.
    """

    start_url: URL | None = None
    storage_key_template: str = "primespiders:{job_uuid}{suffix}"
    default_timeout: int = 30000
    url_filters: Sequence[Callable[[URL], bool]] = ()

    def __init__(self, page: Page):
        self.page = page

        self._accepted_domain: URL | None = None
        self.redis_client = get_redis()
        self.job_uuid = uuid4()

        self.urls_to_visit_key = self.storage_key_template.format(
            job_uuid=self.job_uuid,
            suffix=":urls_to_visit"
        )
        self.visited_urls_key = self.storage_key_template.format(
            job_uuid=self.job_uuid,
            suffix=":visited_urls"
        )
        self.seen_urls_key = self.storage_key_template.format(
            job_uuid=self.job_uuid,
            suffix=":seen_urls"
        )

        if self.redis_client is not None:
            self.redis_client.sadd(self.visited_urls_key, str(self.start_url))

        logger.info(f"Initializing spider with job UUID: {self.job_uuid}")

        self.signals = SignalsContainer(self)
        self.signals.attach(PerformanceObserver())
        self.signals.attach(HistoryObserver())

    def __repr__(self):
        return f"<{self.__class__.__name__} job_uuid={self.job_uuid}>"

    @property
    def get_url_filters(self):
        return self.url_filters

    @property
    def urls_to_visit(self) -> Sequence[URL]:
        """Return the list of URLs to visit from the Redis set."""
        urls: list[URL] = []

        members = self.redis_client.smembers(self.urls_to_visit_key)
        for str_url in members:
            urls.append(URL(str_url))

        return urls if urls else []

    @staticmethod
    async def url_to_str(urls: TypeUrls) -> Sequence[str]:
        str_urls: list[str] = []
        if isinstance(urls, AsyncGenerator):
            async for u in urls:
                str_urls.append(str(u))
        else:
            for u in urls:
                str_urls.append(str(u))
        return str_urls

    @staticmethod
    async def str_to_url(str_urls: Sequence[str], root_domain: str | None = None) -> Sequence[URL]:
        """Convert a sequence of string URLs to a sequence of valid URL objects.
        
        Args:
            str_urls (Sequence[str]): A sequence of string URLs to be converted.
            root_domain (str | None): The root domain to be used for relative URLs.

        Returns:
            Sequence[URL]: A sequence of valid URL objects.
        """
        hrefs = [URL(u, root_domain=root_domain) for u in str_urls]
        return list(filter(lambda u: u.is_not_none, hrefs))

    @abstractmethod
    async def run(self):
        """Run the crawling process starting from the start URL."""
        if self.start_url is None:
            raise ValueError("start_url must be defined")

        self._accepted_domain = URL(self.start_url, root_domain=self._accepted_domain.domain).domain

        logger.info(f"Navigating to start URL: {self.start_url}")
        await self.page.goto(
            str(self.start_url),
            timeout=self.default_timeout,
            wait_until='domcontentloaded'
        )

        try:
            await self.after_initial_navigation()
        except Exception as e:
            logger.error(f"Error during after_initial_navigation: {e}")
        
        urls = await self.get_page_links()
        await self._add_urls_to_redis(urls)

        # This is the section that
        # handles crawling from page to page
        if self.redis_client is not None:
            can_crawl: bool = True
            while can_crawl:
                current_url = self.redis_client.spop(self.urls_to_visit_key, 1)
                if not current_url:
                    logger.info("No more URLs to crawl.")
                    can_crawl = False
                    break

                next_url = URL(
                    current_url[0].decode('utf-8'), 
                    root_domain=self._accepted_domain
                )
                if not next_url.is_valid:
                    continue

                await self.page.goto(
                    str(next_url),
                    timeout=self.default_timeout,
                    wait_until='domcontentloaded'
                )

                urls = await self.get_page_links()

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self._add_urls_to_redis(urls))

                    try:
                        await tg.create_task(self.on_page_actions(current_url, tg=tg))
                    except Exception as e:
                        logger.error(f"Error during on_page_actions for URL {current_url}: {e}")

                    await tg.create_task(self.signals.notify(current_url=next_url))

                    if os.environ.get('DEBUG') == 'True':
                        can_crawl = False
                        break

                await asyncio.sleep(10)

    async def _add_urls_to_redis(self, urls: TypeUrls):
        """Add a sequence or generator of URLs to the Redis sets 
        for URLs to visit and seen links."""

        if self.redis_client is not None:
            all_urls = await self.url_to_str(urls)

            filtered_urls = await self.run_url_filters(urls)
            filtered_str_urls = await self.url_to_str(filtered_urls)

            if not all_urls or not filtered_str_urls:
                return

            self.redis_client.sadd(self.urls_to_visit_key, *filtered_str_urls)
            self.redis_client.sadd(self.seen_urls_key, *all_urls)

    async def automate(self, from_file: str):
        fullpath = pathlib.Path(from_file)
        if not fullpath.exists():
            raise FileNotFoundError(f"The file {from_file} does not exist.")

        if fullpath.is_dir():
            raise IsADirectoryError(f"The path {from_file} is a directory, expected a file.")

        # If the file exists and is not a directory, proceed with automation
        async with aiofiles.open(fullpath, 'r') as f:
            content = io.BytesIO(await f.read())
            if fullpath.suffix == '.csv':
                df = pandas.read_csv(content)
            elif fullpath.suffix == '.json':
                df = pandas.read_json(content)

        if not 'urls' in df.columns:
            raise ValueError(f"The file {from_file} must contain a 'urls' column.")
        
        url_instances: list[URL] = []
        for url in df['urls']:
            instance = URL(url)
            url_instances.append(instance)

        await self._add_urls_to_redis(url_instances)

        can_crawl = True
        while can_crawl:
            next_url = await self.redis_client.spop(self.urls_to_visit_key)
            if next_url is None:
                break

            await self.on_page_actions(next_url, df=df)
            await self.signals.notify(current_url=next_url)
            await asyncio.sleep(10)

    async def get_page_links(self) -> Sequence[URL]:
        await asyncio.sleep(3)

        str_hrefs: list[str] = []

        links = await self.page.query_selector_all('a')
        for item in links:
            href = await item.get_attribute('href')
            str_hrefs.append(href)

        # Do an eval on the page because the "query_selector_all" 
        # method might not capture dynamically generated links.
        hrefs_from_js = await self.page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a'))
            return anchors.map(anchor => anchor.href)
        }""")

        str_hrefs.extend(hrefs_from_js)
        hrefs = await self.str_to_url(str_hrefs)

        logger.info(f"Found {len(hrefs)} valid links on the page.")
        return hrefs

    async def get_page_images(self):
        pass

    async def scrap_page(self):
        pass

    async def run_url_filters(self, urls: TypeUrls) -> Sequence[URL]:
        """Run the URL filters on the given sequence or generator of URLs. This
        function is exclusive in other words it excludes URLs that do not pass 
        all the filters.

        Args:
            urls (TypeUrls):
                The sequence or generator of URLs to be filtered.

        Returns:
            Sequence[URL]: The filtered sequence of URLs.
        """

        def evaluate_func[T = Callable[[URL], bool] | BaseCondition](url: URL, value: T) -> bool:
            result: T = value(url)

            if not isinstance(result, (bool, BaseCondition)):
                raise TypeError(
                    "Expected bool or BaseCondition for "
                    f"filter function {value}, got {type(result)}"
                )

            if isinstance(result, BaseCondition):
                result = result.resolve()

            return result

        # If any of the filters return True,
        # the URL is excluded.
        accepted_urls: list[URL] = []
        for url in urls:
            if not url.check_domain(self._accepted_domain):
                continue

            result = any(evaluate_func(url, func) for func in self.url_filters)
            if result:
                continue

            accepted_urls.append(url)

        logger.info(f"Accepted {len(accepted_urls)} URLs after filtering.")
        return accepted_urls

    async def after_initial_navigation(self):
        """Perform actions after the initial navigation occurs
        on the start URL. This is typically where you would handle 
        things like accepting cookies or closing pop-ups."""

    async def before_page_actions(self):
        """Perform actions before interacting with the page."""

    async def on_page_actions(self, current_url: URL, *, tg: asyncio.TaskGroup | None = None, **kwargs: Any):
        pass
