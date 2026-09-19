import os

import pytest
from playwright.async_api import async_playwright

from src.primespiders.components.bershka.app import Bershka

os.environ.setdefault("DEBUG", "True")


@pytest.mark.e2e
async def test_bershka_spider():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        spider = Bershka(page)
        spider.start_url = 'https://www.bershka.com/fr/minijupe-en-jean-c0p227263455.html?colorId=428'
        await spider.run()

        assert spider is not None
        await browser.close()
