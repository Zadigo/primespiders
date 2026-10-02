import asyncio
from abc import ABC
from base64 import urlsafe_b64encode

from playwright.async_api import ElementHandle

from primespiders.base import BaseSpider, Error, abstractmethod
from primespiders.components.google_maps.models import GooglePlaceModel
from primespiders.typings import BaseSpiderProtocol
from primespiders.utils.urls import URL


class BaseGoogleMaps(ABC):
    @abstractmethod
    def create_dataframe(self):
        pass

    async def automate(self: BaseSpiderProtocol):
        await self.page.wait_for_event('load')

        feed_class = 'div[role="feed"]'
        await self.page.wait_for_selector(feed_class, state='visible')
        # feed = await page.query_selector(feed_class)

        stop_count: int = 0
        last_reference: str = ""

        must_load = True
        places: set[GooglePlaceModel] = set()

        while must_load:
            articles = await self.page.query_selector_all('div[role="article"]')
            last_article = articles[len(articles) - 1]

            for article in articles:
                json_data: dict[str, str] = {}
                
                urlLocator = await article.query_selector('a')
                if urlLocator is not None:
                    parsed_url = URL(await urlLocator.get_attribute('href'))

                    reference = urlsafe_b64encode(str(parsed_url).encode())
                    json_data['reference'] = reference.decode()
                    json_data['url'] = str(parsed_url)
                    json_data['name'] = await urlLocator.inner_text()

                places.add(GooglePlaceModel(**json_data))

            await last_article.scroll_into_view_if_needed(timeout=2000)
            await asyncio.sleep(5)

            # If the last reference is the same as the current one, 
            # increment the stop count and then check if it has 
            # reached the threshold
            if last_reference == json_data.get('reference'):
                stop_count += 1
            last_reference = json_data.get('reference', '')

            if stop_count >= 3:
                must_load = False

            await asyncio.sleep(20)



class GooglePlaces(BaseGoogleMaps, BaseSpider):
    """Google Places spider for scraping places from Google Maps."""

    base_url: str = 'https://www.google.com/maps/search/pharmacie+lille/@50.608788,3.0357762,14z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI2MDkyOS4wIKXMDSoASAFQAw%3D%3D'
    storage_key_template = 'google_places:{query}'

    async def _parse_article(self, article: ElementHandle) -> GooglePlaceModel:
        name = await article.query_selector('a')
        if name is not None:
            name = await name.inner_text()

        url = await article.query_selector('a')
        if url is not None:
            url = await url.get_attribute('href')

        return GooglePlaceModel(name=name, url=url)

    async def before_page_actions(self):
        await self.page.wait_for_selector('body')
        buttons = await self.page.query_selector_all('button')
        for button in buttons:
            text = await button.inner_text()
            if text.strip().lower() == "tout accepter":
                try:
                    await button.click(button='left')
                except Error as e:
                    print(f"Error clicking 'Tout accepter' button: {e}")
                break

    async def on_page_actions(self, current_url, *, tg = None, **kwargs):
        pass
            

class GooglePlace(BaseGoogleMaps, BaseSpider):
    """Google Place spider for scraping a single place from Google Maps."""

    base_url: str = 'https://www.google.com/maps/place/Grande+Pharmacie+de+Lille/@50.61921,3.0031802,14z/data=!4m10!1m2!2m1!1spharmacie+lille!3m6!1s0x47c2d573496fa237:0x2dd485f0ab4a9155!8m2!3d50.61921!4d3.041289!15sCg9waGFybWFjaWUgbGlsbGVaESIPcGhhcm1hY2llIGxpbGxlkgEIcGhhcm1hY3ngAQA!16s%2Fg%2F1v16pg3_?entry=ttu&g_ep=EgoyMDI2MDkyOS4wIKXMDSoASAFQAw%3D%3D'

    async def on_page_actions(self, current_url, *, tg = None, **kwargs):
        pass


# class SearchLinks(BaseGoogleMaps, BaseSpider):
#     pass


# class SearchBusiness(BaseGoogleMaps, BaseSpider):
#     pass
