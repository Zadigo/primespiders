from unittest.mock import AsyncMock, Mock, patch

import pytest
from playwright.async_api import Browser, ElementHandle, Page

from primespiders.base import BaseSpider
from primespiders.observer import SignalsContainer
from primespiders.utils import ENV
from primespiders.utils.urls import URL

# os.environ.setdefault('DEBUG', 'True')

ENV(DEBUG='true')


@pytest.fixture
def mock_page():
    return Mock(
        spec=Page,
        goto=AsyncMock(),
        evaluate=AsyncMock(
            return_value=[
                'http://example.com/3'
            ]
        ),
        query_selector_all=AsyncMock(
            return_value=[
                Mock(
                    spec=ElementHandle,
                    get_attribute=AsyncMock(
                        return_value='http://example.com/1'
                    )
                ),
                Mock(
                    spec=ElementHandle,
                    get_attribute=AsyncMock(
                        return_value='http://example.com/2'
                    )
                )
            ]
        )
    )


@pytest.fixture
def mock_browser():
    return Mock(spec=Browser)


@pytest.fixture
def mock_spider(mock_page):
    class FakeSpider(BaseSpider):
        async def run(self, *args, **kwargs):
            return await super().run(*args, **kwargs)

    with (
        patch('primespiders.base.SignalsContainer', new_callable=Mock, spec=SignalsContainer),
        patch('primespiders.base.get_redis') as redisclient,
        patch.object(BaseSpider, 'get_page_links', new_callable=AsyncMock) as plinks,
        patch.object(BaseSpider, '_add_urls_to_redis', new_callable=AsyncMock)
    ):
        plinks.return_value = ['http://example.com/1', 'http://example.com/2']
        redisclient.return_value = Mock(
            sadd=Mock(),
            spop=Mock(
                return_value=[b'http://example.com/1']
            )
        )

        return FakeSpider(page=mock_page)


@pytest.fixture
def mock_automation_spider(mock_page):
    class FakeAutomationSpider(BaseSpider):
        async def run(self, *args, **kwargs):
            return await super().run(*args, **kwargs)

    with (
        patch('primespiders.base.SignalsContainer', new_callable=Mock, spec=SignalsContainer),
        patch('primespiders.base.get_redis'),
    ):
        return FakeAutomationSpider(page=mock_page, automation=True)


async def test_crawl_spider_initialization(mock_spider):
    assert mock_spider.can_crawl is True


async def test_crawl_spider_run_no_start_url(mock_spider, mock_browser):
    with pytest.raises(ValueError):
        await mock_spider.run(mock_browser)


async def test_crawl_spider_run_start_url(mock_spider, mock_browser):
    mock_spider.start_url = URL('http://example.com')
    await mock_spider.run(mock_browser)


async def test_automation_spider_initialization(mock_automation_spider):
    assert mock_automation_spider.can_crawl is True
    assert mock_automation_spider.storage_key_template.endswith('automation')


async def test_url_filters(mock_automation_spider):
    urls = [
        URL('http://example.com/1', root_domain='example.com'),
        URL('http://example.com/2', root_domain='example.com'),
        URL('http://other.com/1', root_domain='other.com')
    ]
    filtered_urls = await mock_automation_spider.run_url_filters(urls)
    assert all(url.check_domain('example.com') for url in filtered_urls)
    assert all(url.root_domain == 'example.com' for url in filtered_urls)
