from base import BaseSpider, EcommerceMixin
from components.bershka.url_filters import remove_static_page
from utils.operators import And, PartTest, Q, Rules


class Bershka(EcommerceMixin, BaseSpider):
    start_url: str | None = "https://www.bershka.com/"
    url_filters = (
        remove_static_page,
    )

    async def run(self):
        await super().run()

    async def after_initial_navigation(self):
        element = await self.page.wait_for_selector('#onetrust-banner-sdk', state='visible', timeout=10000)

        if element is not None:
            state = self.page.query_selector(
                'button#onetrust-accept-btn-handler')
            if state is not None:
                await state.click()

    async def check_is_category_page(self, url):
        conditions = [
            Q(Rules.CONTAINS, "femmes"),
            Q(Rules.CONTAINS, "vetements"),
            PartTest(url, "celement", part='query')
        ]
        return And(url, *conditions)
