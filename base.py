import asyncio
import os
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable, Sequence
from uuid import uuid4

from playwright.async_api import Page
from primespiders.observer import HistoryObserver, PerformanceObserver, SignalsContainer
from primespiders.utils import logger
from primespiders.utils.clients import get_redis
from primespiders.utils.urls import URL

from typings import EcommerceMixinProtocol, TypeUrls
from utils.operators import BaseCondition


class EcommerceMixin[T= 'BaseSpider']:
    def check_is_product_page(self: EcommerceMixinProtocol, url: URL) -> bool:
        """Implement this method to check if the given URL corresponds to a product page."""
        return False

    def check_is_category_page(self: EcommerceMixinProtocol, url: URL) -> bool:
        """Implement this method to check if the given URL corresponds to a category page."""
        return False


class BaseSpider(ABC):
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

    async def get_page_links(self) -> Sequence[URL]:
        hrefs: list[URL] = []
        links = await self.page.query_selector_all('a')
        for item in links:
            href = await item.get_attribute('href')
            if href is None:
                continue

            href_instance = URL(href)

            if href_instance.is_valid:
                hrefs.append(href_instance)
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

            if isinstance(result, BaseCondition):
                result = result.resolve()

            return result

        # If any of the filters return True,
        # the URL is excluded.
        accepted_urls: list[URL] = []
        if isinstance(urls, AsyncGenerator):
            async for url in urls:
                if any(evaluate_func(url, func) for func in self.url_filters):
                    continue
                accepted_urls.append(url)
        else:
            for url in urls:
                if any(evaluate_func(url, func) for func in self.url_filters):
                    continue
                accepted_urls.append(url)
        return accepted_urls

    async def after_initial_navigation(self):
        """Perform actions after the initial navigation occurs
        on the start URL. This is typically where you would handle 
        things like accepting cookies or closing pop-ups."""

    async def before_page_actions(self):
        """Perform actions before interacting with the page."""

    async def on_page_actions(self, current_url: URL):
        pass

    @abstractmethod
    async def run(self):
        """Run the crawling process starting from the start URL."""
        if self.start_url is None:
            raise ValueError("start_url must be defined")

        self._accepted_domain = URL(self.start_url).domain

        logger.info(f"Navigating to start URL: {self.start_url}")
        await self.page.goto(
            str(self.start_url),
            timeout=self.default_timeout,
            wait_until='domcontentloaded'
        )

        await self.after_initial_navigation()

        urls = await self.get_page_links()
        await self._add_urls_to_redis(urls)

        # This is the section that
        # handles crawling from page to page
        if self.redis_client is not None:
            can_crawl: bool = True
            while can_crawl:
                current_url = self.redis_client.spop(self.urls_to_visit_key, 1)
                if not current_url:
                    can_crawl = False
                    break

                next_url = URL(current_url[0].decode(
                    'utf-8'), domain=self._accepted_domain)
                if not next_url.is_valid:
                    continue

                await self.page.goto(
                    str(next_url),
                    timeout=self.default_timeout,
                    wait_until='domcontentloaded'
                )

                urls = await self.get_page_links()
                await self._add_urls_to_redis(urls)

                await self.on_page_actions(current_url)
                await self.signals.notify(current_url=next_url)

                if os.environ.get('PRIMESPIDERS_ENV') == 'test':
                    can_crawl = False
                    break

                await asyncio.sleep(10)
