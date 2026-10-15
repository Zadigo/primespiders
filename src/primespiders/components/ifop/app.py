import asyncio
import io

import httpx2

from primespiders.base import AutomationSpider
from primespiders.components.ifop.models import IfopStudyModel
from primespiders.utils.dates import parse_date
from primespiders.utils.urls import URL

# from primespiders.utils.decorators import prevent_side_effects


# @prevent_side_effects
async def download_pdf_file(spider: AutomationSpider, model: IfopStudyModel):
    async with asyncio.Semaphore(5), httpx2.AsyncClient() as client:
        files = spider.redis_client.smembers(spider.processed_data_storage_key)
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
                    spider.redis_client.sadd(spider.processed_data_storage_key, model.pdf_url)

                await spider.signals.notify(
                    file_content=io.BytesIO(response.content),
                    file_key=f"{model.slug}.pdf",
                    tag='s3'
                )


class IfopSpider(AutomationSpider):
    start_url = URL("https://www.ifopgroup.com/journalistes/?s=&search_marques%5B%5D=ifop-opinion")

    async def before_page_actions(self):
        if self.redis_client is not None:
            current_page = self.redis_client.get(self.pagination_storage_key)
            if current_page is None:
                current_page = 1
                self.redis_client.set(self.pagination_storage_key, current_page)

    async def after_page_actions(self):
        if self.redis_client is not None:
            self.redis_client.incr(self.pagination_storage_key)
            
            pagination_handles = await self.page.query_selector_all('li.pagination__item')
            for index, handle in enumerate(pagination_handles):
                if index == self.redis_client.get(self.pagination_storage_key):
                    break

            await handle.click()
            async with self.page.expect_navigation():
                await self.page.wait_for_selector('.section__search-grid')

    async def on_page_actions(self, current_url: URL, **kwargs):
        articles = await self.page.query_selector_all('.card__journalist')

        async with asyncio.TaskGroup() as tg:
            for article in articles:
                json_data: dict = {}

                date_handle = await article.query_selector('.card__journalist-date')
                if date_handle is not None:
                    str_date = await date_handle.inner_text()
                    date = parse_date(str_date)
                    if date is not None:
                        json_data['date'] = date.isoformat()

                title_handle = await article.query_selector('h3.card__journalist-title')
                if title_handle is not None:
                    json_data['title'] = await title_handle.inner_text()

                abstract_handle = await article.query_selector('p.card__journalist-description')
                if abstract_handle is not None:
                    json_data['abstract'] = await abstract_handle.inner_text()

                pdf_handle = await article.query_selector('a.card__journalist-download')
                if pdf_handle is not None:
                    json_data['pdf_url'] = await pdf_handle.get_attribute('href')

                model = IfopStudyModel(**json_data)
                if model.url is not None:
                    await self.page.goto(str(model.url))
                    await self.page.wait_for_event('load')

                    abstract_title = await self.page.query_selector('.single__post-title')
                    if abstract_title is not None:
                        model.abstract_title = await abstract_title.inner_text()

                    abstract_text = await self.page.query_selector('.acf-innerblocks-container')
                    if abstract_text is not None:
                        model.abstract_text = await abstract_text.inner_text()

                    await self.page.go_back()
                    await asyncio.sleep(1)

                # task = tg.create_task(download_pdf_file(self, model))
                # task.add_done_callback(done_callback)
                # BACKGROUND_TASKS.add(task)

                self.redis_client.sadd(
                    self.processed_data_storage_key, 
                    model.slug
                )

