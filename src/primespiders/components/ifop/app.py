import asyncio
import io

import httpx2

from primespiders.base import AutomationSpider
from primespiders.components.ifop.models import IfopStudyModel
from primespiders.utils.dates import parse_date


async def download_pdf_file(spider: AutomationSpider, model: IfopStudyModel):
    async with asyncio.Semaphore(5), httpx2.AsyncClient() as client:
        files = spider.redis_client.smembers(spider.processed_storage_key)
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
                    spider.redis_client.sadd(spider.processed_storage_key, model.pdf_url)

                spider.signals.notify(
                    file_content=io.BytesIO(response.content),
                    file_key=f"{model.slug}.pdf",
                    tag='s3'
                )


class IfopSpider(AutomationSpider):
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

    async def on_page_actions(self, current_url, **kwargs):
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
                tg.create_task(download_pdf_file(self, model))

                if self.redis_client is not None:
                    self.redis_client.sadd(self.processed_storage_key, model.slug)

