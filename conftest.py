from unittest.mock import AsyncMock, Mock

import pytest
from playwright.async_api import Page


@pytest.fixture
def playwright_page():
    return AsyncMock(spec=Page)


@pytest.fixture
def base_spider(playwright_page):
    from src.primespiders.base import BaseSpider

    class SimpleSpider(BaseSpider):
        def __init__(self, page: Page):
            super().__init__(page)
            self.job_uuid = 'test_uuid'
            
        async def run(self):
            await super().run()

    return SimpleSpider(playwright_page)


@pytest.fixture
def mocked_query_selector():
    """Creates a mock for query_selector_all 
    that returns the given URLs."""
    urls = [
        'http://example.com/page1',
        'http://example.com/page2',
        'http://example.com/invalid-page'
    ]

    return AsyncMock(
        return_value=[
            Mock(
                get_attribute=AsyncMock(
                    return_value=url
                )
            )
            for url in urls
        ]
    )
