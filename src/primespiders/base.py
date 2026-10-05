import asyncio
import contextlib
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any
from uuid import uuid4

import pydantic
from playwright.async_api import Browser, Page
from simplecron import base as simplecron_base

from primespiders.observer import (
    HistoryCrawlObserver,
    PerformanceCrawlObserver,
    RedisChannelObserver,
    SignalsContainer,
)
from primespiders.typings import EcommerceMixinProtocol, TypeUrls
from primespiders.utils import ENV, logger
from primespiders.utils.clients import get_redis
from primespiders.utils.operators import BaseCondition
from primespiders.utils.urls import URL

IN_BETWEEN_PAGE_DELAY = ENV.integer('IN_BETWEEN_PAGE_DELAY', default=10)

DEFAULT_TIMEOUT = ENV.integer('DEFAULT_TIMEOUT', default=10000)

_background_tasks: set[asyncio.Task[Any]] = set()


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


class MultiTabRunner:
    """Method wrapper for enabling multi-tab mode in spiders."""

    def __init__(self):
        self.pages: list[Page] = []

    async def __call__(self, spider: BaseSpider, urls: Sequence[URL], **kwargs):
        if not self.pages:
            for _ in range(len(urls)):
                page = await spider.browser.new_page()
                self.pages.append(page)

        for index, url in enumerate(urls):
            try:
                page = self.pages[index]
                await page.goto(str(url), timeout=2000, wait_until="domcontentloaded")
            except (TypeError, ValueError) as e:
                logger.error(f"Error processing URL {url}: {e}")
            else:
                await asyncio.sleep(1)

            try:
                await spider.on_page_actions(url, page=page, **kwargs)
            except (TypeError, ValueError) as e:
                logger.error(f"Error processing URL {url}: {e}")


class CallbackRunner:
    """Method wrapper for enabling callback execution in spiders."""

    def __init__(self, spider: BaseSpider):
        self._spider = spider

    async def __call__(self, *args, **kwargs):
        asyncio.create_task(self._spider.callback_function(*args, **kwargs))


class BaseSpider(ABC):
    """Base class for all spiders.

    Args:
        page (Page): The Playwright page instance for the spider.
        with_id (str | None): The unique identifier for the spider instance.
        automation (bool): Whether the spider is running in automation mode.

    Attributes:
        start_url (URL | None): The starting URL for the spider.
        storage_key_template (str): Template for Redis storage keys.
        default_timeout (int): Default timeout for requests.
        base_url_filters (Sequence[Callable[[URL], bool]]): Filters to apply to URLs.
        ignore_queries (bool): Whether to ignore URLs with query parameters when crawling.
        ignore_fragments (bool): Whether to ignore URLs with URL fragments when crawling.
        multi_tab_mode (bool): Whether to enable multi-tab mode for the spider.
        automation (bool): Whether the spider is running in automation mode.
        signals (SignalsContainer): The container for managing spider signals.
        can_crawl (bool): Whether the spider can keep crawling to discover and visit new pages.
    """

    start_url: URL | None = None
    # storage_key_template: str = "primespiders:{job_uuid}{suffix}"
    default_timeout: int = DEFAULT_TIMEOUT
    base_url_filters: Sequence[Callable[[URL], bool]] = ()
    ignore_queries: bool = True
    ignore_fragments: bool = True
    multi_tab_mode: bool = False
    automation: bool = False

    def __init__(self, page: Page, *, with_id: str | None = None):
        self.browser: Browser | None = None
        self.page = page

        self._accepted_domain: str | None = None
        self.redis_client = get_redis()
        self.job_uuid = with_id or uuid4()

        logger.info(f"Initializing spider with job UUID: {self.job_uuid}")

        self.signals = SignalsContainer(self)
        self.signals.attach(RedisChannelObserver())

        if not self.automation:
            self.signals.attach(PerformanceCrawlObserver())
            self.signals.attach(HistoryCrawlObserver())

        self.can_crawl: bool = True

        if not self.automation and bool(self.redis_client):
            self.redis_client.sadd(
                self.urls_to_visit_storage_key,
                str(self.start_url)
            )

    def __repr__(self):
        return f"<{self.__class__.__name__} job_uuid={self.job_uuid}>"

    @property
    def get_url_filters(self):
        return self.base_url_filters

    @property
    def urls_to_visit_storage_key(self):
        return f"{self.__class__.__name__}:{self.job_uuid}:urls_to_visit"

    @property
    def visited_urls_storage_key(self):
        return f"{self.__class__.__name__}:{self.job_uuid}:visited_urls"

    @property
    def seen_urls_storage_key(self):
        return f"{self.__class__.__name__}:{self.job_uuid}:seen_urls"

    @property
    def pagination_storage_key(self):
        """Redis storage key for pagination state."""
        return f"{self.__class__.__name__}:{self.job_uuid}:pagination"

    @property
    def processed_storage_key(self):
        """Redis storage key for processed files, urls..."""
        return f"{self.__class__.__name__}:{self.job_uuid}:processed"

    @property
    def performance_storage_key(self):
        """Redis storage key for performance data."""
        return f"{self.__class__.__name__}:{self.job_uuid}:performance"

    @property
    def urls_to_visit(self) -> Sequence[URL]:
        """Return the list of URLs to visit from the Redis set."""
        urls: list[URL] = []

        members = self.redis_client.smembers(self.urls_to_visit_storage_key)
        for str_url in members:
            urls.append(URL(str_url))

        return urls if urls else []

    @staticmethod
    async def url_to_str(urls: TypeUrls) -> Sequence[str]:
        str_urls: list[str] = []
        for url in urls:
            str_urls.append(str(url))
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
    async def callback_function(self, event: asyncio.Event, *args, **kwargs):
        pass

    async def run(self, browser: Browser, ignore_queries: bool = True, ignore_fragments: bool = True):
        """Main entrypoint that runs either the automation or the crawling process.
        Args:
            browser (Browser): The Playwright browser instance to use for interactions.
            ignore_queries (bool): Whether to ignore URLs with query parameters.
            ignore_fragments (bool): Whether to ignore URLs with URL fragments.

        Raises:
            ValueError: If the start URL is not defined.
        """
        self.browser = browser
        self.ignore_queries = ignore_queries
        self.ignore_fragments = ignore_fragments

        if self.start_url is None:
            raise ValueError("start_url must be defined")

        self._accepted_domain = URL(self.start_url).domain

        logger.info(f"Navigating to start URL: {self.start_url}")
        await self.page.goto(
            str(self.start_url),
            timeout=self.default_timeout,
            wait_until='domcontentloaded'
        )

        try:
            await self.after_initial_navigation()
        except (TypeError, ValueError) as e:
            logger.error(f"Error during after_initial_navigation: {e}")

        default_interval = 10 if self.automation else 40
        interval = ENV.integer('SPIDER_INTERVAL', default=default_interval)
        # ENV.conditional('SPIDER_INTERVAL').greater_than_equal_to(10)

        debug_mode = ENV.boolean('DEBUG', default=False)
        if debug_mode:
            interval = 1

        logger.info(f"Spider interval set to {interval} seconds.")

        # Shared event used to control the state 
        # of the automation or crawling loop.
        stop_event: asyncio.Event = asyncio.Event()


        job = simplecron_base.every(interval).seconds
        if debug_mode:
            job.with_limited_runs(3).do(self.callback_function, event=stop_event)
        else:
            job.do(self.callback_function, event=stop_event)

        context: dict[str, Any] = {}

        while not stop_event.is_set():
            if context is not None:
                context["stop_event"] = stop_event

            try:
                while not stop_event.is_set():
                    simplecron_base.run_pending(context=context)
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            finally:
                await simplecron_base._shutdown()

        # def runner(*args, **kwargs):
        #     asyncio.create_task(self.callback_function(event=event))

        # This is the main section that handles the scheduling 
        # and execution of the automation or crawling tasks.
        # schedule.every(interval).seconds.do(runner)
    
        # wrapped_func = CallbackRunner(self)
        # schedule.every(interval).seconds.do(lambda: asyncio.create_task(wrapped_func()))
        # schedule.run_pending()
        # await asyncio.sleep(1)

        # if debug_mode:
        #     event.clear()
        #     logger.info("Debug mode active, stopping automation loop.")

    async def _add_urls_to_redis(self, urls: TypeUrls):
        """Add a sequence or generator of URLs to the Redis sets 
        for URLs to visit and seen links."""

        if self.redis_client is not None:
            all_urls = await self.url_to_str(urls)

            filtered_urls = await self.run_url_filters(urls)
            filtered_str_urls = await self.url_to_str(filtered_urls)

            if not all_urls or not filtered_str_urls:
                return

            self.redis_client.sadd(self.urls_to_visit_storage_key, *filtered_str_urls)
            self.redis_client.sadd(self.seen_urls_storage_key, *all_urls)

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
        hrefs = await self.str_to_url(str_hrefs, root_domain=self._accepted_domain)

        logger.info(f"Found {len(hrefs)} valid links on the page.")
        return hrefs

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

        # If any of the filters return True, the URL is excluded.
        accepted_urls: list[URL] = []
        for url in urls:
            if url.root_domain is None:
                url.root_domain = self._accepted_domain

            # These are basic URL filters that are applied: domain check, 
            # fragments and queries
            if not url.is_path and not url.check_domain(self._accepted_domain):
                continue

            if self.ignore_fragments and bool(url.parsed_url.fragment):
                continue

            if self.ignore_queries and bool(url.parsed_url.query):
                continue
                
            # These are custom more complex URL filters
            result = any(evaluate_func(url, func) for func in self.get_url_filters)
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
        """Perform actions on the page after it has been loaded."""

    async def after_page_actions(self):
        """Perform actions after interacting with the page."""


class AutomationSpider(BaseSpider):
    automation = True
    
    async def callback_function(self, *args, event: asyncio.Event | None = None, from_file: str | None = None, **kwargs):
        await self.on_page_actions(self.start_url, event=event, **kwargs)
        await self.after_page_actions()


class CrawlerSpider(BaseSpider):
    async def callback_function(self, *args, event: asyncio.Event | None = None, **kwargs):
        current_url = self.redis_client.spop(self.urls_to_visit_storage_key, 1)
        if not current_url:
            logger.info("No more URLs to crawl.")
            self.can_crawl = False
            return

        next_url = URL(
            current_url[0].decode('utf-8'), 
            root_domain=self._accepted_domain
        )
        if not next_url.is_valid:
            logger.warning(f"Invalid URL encountered: {next_url}")
            return

        logger.info(f"Navigating to next URL: {next_url}")
        await self.page.goto(
            str(next_url),
            timeout=self.default_timeout,
            wait_until='domcontentloaded'
        )

        self.redis_client.sadd(self.visited_urls_storage_key, str(next_url))
        urls = await self.get_page_links()

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._add_urls_to_redis(urls))

            try:
                await tg.create_task(self.on_page_actions(current_url, event=event, tg=tg))
            except (TypeError, ValueError) as e:
                logger.error(f"Error during on_page_actions for URL {current_url}: {e}")

            await tg.create_task(self.signals.notify(current_url=next_url))

        await asyncio.sleep(IN_BETWEEN_PAGE_DELAY)

        if ENV.boolean('DEBUG', default=False):
            self.can_crawl = False
            return
