from unittest.mock import Mock

import pytest
from playwright.async_api import async_playwright

from primespiders.components.eustudies.app import EuStudies, download_pdf_file
from primespiders.components.eustudies.models import EuStudyModel


@pytest.fixture
def study_fixture():
    return EuStudyModel(
        study_type='Analytical reports',
        year=2024,
        abstract="Drawing on the 2024 and 2025 open data maturity assessments, this report explores how European countries are advancing open data maturity. It presents country best practices across the policy, portals, quality and impact thematic dimensions of the assessment. The report offers practical guidance and inspiration for governments seeking to strengthen their open data ecosystems.",
        pdf_url='https://data.europa.eu/sites/default/files/report/report-2025-odm-best-practices.pdf',
        title="2025 open data best practices in Europe",
    )


@pytest.mark.e2e
async def test_download_pdf_file(study_fixture):
    await download_pdf_file(
        Mock(
            storage_key_template='dummy_storage_key',
            redis_client=Mock(
                smembers=Mock(
                    return_value=set()
                )
            )
        ), 
        study_fixture
    )


@pytest.mark.e2e
async def test_eustudies_spider():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        spider = EuStudies(page)
        await spider.run(browser)
        await browser.close()
