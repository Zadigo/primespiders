import logging
from unittest.mock import Mock

import pytest
from playwright.async_api import async_playwright

from primespiders.components.bershka.app import Bershka
from primespiders.components.courtaudit.app import CourtAuditSpider, get_pdf_content

# from primespiders.utils import ENV
from primespiders.utils.urls import URL

logger = logging.getLogger(__name__)

# ENV(DEBUG='true')

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


@pytest.mark.e2e
class TestCourtAuditSpider:
    async def test_get_pdf_content(self):
        spider = Mock()
        url = URL('https://www.ccomptes.fr/sites/default/files/2026-09/20261001-S2026-0891-Agence-de-l-innovation-de-defense-AID.pdf')
        await get_pdf_content(spider, url)

    async def test_live_spider(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.wait_for_selector('body')

            spider = CourtAuditSpider(page)
            await spider.run()
            await browser.close()
