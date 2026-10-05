import asyncio
import io

import httpx2
from playwright.async_api import ElementHandle, Page

from primespiders.base import AutomationSpider
from primespiders.components.courtaudit.models import PublicationModel
from primespiders.observer import JsonFileObserver, S3Observer
from primespiders.utils import logger
from primespiders.utils.slug import create_slug
from primespiders.utils.urls import URL


async def get_pdf_content(spider: AutomationSpider, url: URL, model: PublicationModel):
    async with asyncio.Semaphore(10), httpx2.AsyncClient(timeout=10) as client:
        file_key = f'rapports-cours-compte/{model.slug}.pdf'
        if file_key in spider.redis_client.smembers('uploaded_files'):
            return

        try:
            response = await client.get(str(url))
            response.raise_for_status()
        except httpx2.HTTPStatusError as e:
            logger.error(f"Failed to fetch PDF content from {url}: {e}")
            return
        except (TimeoutError, httpx2.RequestError) as e:
            logger.error(f"Failed to fetch PDF content from {url}: {e}")
            return
        else:
            buffer = io.BytesIO(response.content)
            spider.redis_client.sadd('uploaded_files', file_key)

            await spider.signals.notify(
                file_key=f'rapports-cours-compte/{model.slug}.pdf',
                file_content=buffer
            )
        

class CourtAuditSpider(AutomationSpider):
    start_url = URL('https://www.ccomptes.fr/fr/publications?f%5B0%5D=institution%3A98%3Fpage%3D360&page=0')

    def __init__(self, page: Page, **kwargs):
        super().__init__(page, **kwargs)

        self.signals.attach(S3Observer())
        self.signals.attach(JsonFileObserver('audit_files.pdf'))
        
        self.automation = True

    async def run(self, **kwargs):
        await super().run(**kwargs)

    async def on_page_actions(self, current_url, **kwargs):
        state = self.redis_client.get('started')
        if state is None:
            self.redis_client.set('started', 'true')
        else:
            state = state.decode() == 'true'
            if not state:
                self.redis_client.set('started', 'true')
            
        results = await self.page.query_selector_all('li.search-result')

        links: list[str] = []
        for result in results:
            link_loc = await result.query_selector('a')
            if link_loc is not None:
                link = await link_loc.get_attribute('href')
                links.append(URL(link, root_domain=self.start_url.domain))


        for link in links:
            model = PublicationModel()

            await self.page.goto(str(link))

            title_handle= await self.page.query_selector('h1')
            if title_handle is not None:
                model.title = await title_handle.inner_text()
                model.slug = create_slug(model.title)

            theme_handle = await self.page.query_selector('span.text-thematic')
            if theme_handle is not None:
                model.theme = await theme_handle.inner_text()
                theme_url_handle = await theme_handle.query_selector('a')
                if theme_url_handle is not None:
                    model.theme_url = await theme_url_handle.get_attribute('href')

            date_handle = await self.page.query_selector('time.date.section')
            if date_handle is not None:
                str_date = await date_handle.get_attribute('datetime')
                model.date = str_date

            more_button_handle = await self.page.query_selector('button.btn.show-more')
            if more_button_handle is not None:
                await more_button_handle.click()
                await self.page.wait_for_timeout(1000)  # Wait for 1 second to allow content to load

            teaser_content_handle = await self.page.query_selector('div[class^="publication-teaser-content"]')
            if teaser_content_handle is not None:
                model.summary = await teaser_content_handle.inner_text()

            download_handle = await self.page.query_selector('div.links-with-buttons .side')
            if download_handle is not None:
                pdf_loc = await download_handle.query_selector('a')
                if pdf_loc is not None:
                    str_href = await pdf_loc.get_attribute('href')
                    url_object = URL(str_href, root_domain=self.start_url.domain)
                    model.pdf_url = str(url_object)

                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(get_pdf_content(self, url_object, model))
            await self.signals.notify(current_url=self.start_url, tag='json')
            
            await self.page.go_back()
            await asyncio.sleep(2)

        next_page_handle: ElementHandle | None = None
        pagination_handles = await self.page.query_selector_all('li.pager-item')
        for index, item in enumerate(pagination_handles):
            link_loc = await item.query_selector('a')
            loc_class = await item.get_attribute('class')
            
            if 'pager-current' in loc_class:
                if index + 1 < len(pagination_handles):
                    next_page_handle = pagination_handles[index + 1]
                break

        if next_page_handle is not None:
            await next_page_handle.click()
            async with self.page.expect_event('load'):
                self.redis_client.incr('current_page')
                self.redis_client.set('current_page_url', str(self.start_url.increment()))

