import os
from unittest.mock import AsyncMock, Mock

import pytest

from utils.operators import Q, Rules

os.environ.setdefault('PRIMESPIDERS_ENV', 'test')


@pytest.mark.parametrize(
    'testcase,urls',
    [
        (
            'found no urls',
            []
        ),
        (
            'found some urls',
            [
                'http://example.com/page1',
                'http://example.com/page2'
            ]
        ),
    ]
)
async def test_base_spider_runs(base_spider, testcase, urls):
    base_spider.start_url = "http://example.com"
    base_spider.page.query_selector_all = AsyncMock(
        return_value=[
            Mock(
                get_attribute=AsyncMock(
                    return_value=url
                )
            )
            for url in urls
        ]
    )
    await base_spider.run()


async def test_with_filters(base_spider, mocked_query_selector):
    base_spider.start_url = "http://example.com"
    base_spider.url_filters = [
        lambda url: "page1" in str(url),
        lambda url: Q(Rules.CONTAINS, "invalid-page")(url)
    ]
    base_spider.page.query_selector_all = mocked_query_selector
    await base_spider.run()
