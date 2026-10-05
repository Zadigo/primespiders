import pytest
from playwright.async_api import async_playwright

from primespiders.components.ifop.app import IfopSpider
from primespiders.utils import ENV

ENV(DEBUG='true')

@pytest.mark.e2e
async def test_ifop_spider():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        spider = IfopSpider(page)
        await spider.run(browser)
        await browser.close()
