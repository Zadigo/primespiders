import os
from unittest.mock import AsyncMock, Mock

import pytest

from primespiders.utils.operators import Q, Rules

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
async def test_base_spider_runs(spider_fixture, testcase, urls):
    spider_fixture.start_url = "http://example.com"
    spider_fixture.page.query_selector_all = AsyncMock(
        return_value=[
            Mock(
                get_attribute=AsyncMock(
                    return_value=url
                )
            )
            for url in urls
        ]
    )
    await spider_fixture.run()


async def test_with_filters(spider_fixture, mocked_query_selector):
    spider_fixture.start_url = "http://example.com"
    spider_fixture.url_filters = [
        lambda url: "page1" in str(url),
        lambda url: Q(Rules.CONTAINS, "invalid-page")(url)
    ]
    spider_fixture.page.query_selector_all = mocked_query_selector
    await spider_fixture.run()
