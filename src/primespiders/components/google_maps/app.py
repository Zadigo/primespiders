from abc import ABC

from src.primespiders.base import BaseSpider, abstractmethod


class BaseGoogleMaps(ABC):
    @abstractmethod
    def create_dataframe(self):
        pass


class GooglePlaces(BaseGoogleMaps, BaseSpider):
    """Google Places spider for scraping places from Google Maps."""

    base_url: str = 'https://www.google.com/maps/search/pharmacie+lille/@50.608788,3.0357762,14z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI2MDkyOS4wIKXMDSoASAFQAw%3D%3D'

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
