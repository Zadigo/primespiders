import asyncio
import io

import httpx2
from playwright.async_api import ElementHandle

from primespiders.base import BaseSpider
from primespiders.components.eustudies.models import EuStudyModel
from primespiders.observer import JsonFileObserver, S3Observer
from primespiders.utils.urls import URL


async def parse_article(spider: EuStudies, tg: asyncio.TaskGroup, article: ElementHandle):
    model = EuStudyModel()

    metadata_handle = await article.query_selector_all('.ecl-file__detail-meta li')
    if metadata_handle:
        model.study_type = await metadata_handle[0].inner_text()
        model.year = await metadata_handle[-1].inner_text()

    title_handle = await article.query_selector('.ecl-file__title')
    if title_handle:
        model.title = await title_handle.inner_text()

    more_button_handle = await article.query_selector('[class^="ecl-button ecl-button"][type="button"]')
    if more_button_handle:
        await more_button_handle.click(button='left', timeout=1000)

        inner_box_handle = await article.query_selector('.inner-box')
        if inner_box_handle:
            model.abstract = await inner_box_handle.inner_text()

    download_link_handle = await article.query_selector('a[href$=".pdf"]')
    if download_link_handle:
        model.pdf_url = await download_link_handle.get_attribute('href')

    spider.signals.notify(data=model.model_dump(), tag='json')
    tg.create_task(download_pdf_file(spider, model))


async def download_pdf_file(spider: EuStudies, model: EuStudyModel):
    async with asyncio.Semaphore(5), httpx2.AsyncClient() as client:
        storage_key = spider.storage_key_template + ':downloaded'
        files = spider.redis_client.smembers(storage_key)
        if spider.redis_client is not None and model.pdf_url in files:
            return
        
        if model.pdf_url is not None:
            try:
                response = await client.get(model.pdf_url)
                response.raise_for_status()
            except httpx2.HTTPError as e:
                print(f"Failed to download PDF for {model.title}: {e}")
            except (TypeError, ValueError, AttributeError) as e:
                print(f"Failed to download PDF for {model.title}: {e}")
            else:
                if spider.redis_client is not None:
                    spider.redis_client.sadd(storage_key, model.pdf_url)

                spider.signals.notify(
                    file_content=io.BytesIO(response.content),
                    file_key=f"{model.title}.pdf",
                    tag='s3'
                )


class EuStudies(BaseSpider):
    start_url = URL('https://data.europa.eu/en/publications/studies?search=&keywords=&sort_by=published_on&sort_order=DESC&items_per_page=50')
    storage_key_template = 'primespiders:eustudies'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals.attach(S3Observer())
        self.signals.attach(JsonFileObserver('eustudies'))
        self.automation = True

    async def run(self, *args, **kwargs):
        await super().run(*args, **kwargs)

    async def on_page_actions(self, current_url, **kwargs):
        view_content_handle = await self.page.wait_for_selector('.view-content')

        # select_loc = await self.page.query_selector('select[id^="edit-items-per-page"]')
        # if select_loc:
        #     await select_loc.click()
        #     await self.page.wait_for_timeout(1000)
        #     await self.page.select_option(select_loc, value="50", timeout=1000)

        if view_content_handle is not None:
            articles = await view_content_handle.query_selector_all('.views-row article')
            async with asyncio.TaskGroup() as tg:
                for article in articles:
                    tg.create_task(parse_article(self, tg, article))
                    await asyncio.sleep(1)

        if self.redis_client is not None:
            self.redis_client.set('started', 'true')
