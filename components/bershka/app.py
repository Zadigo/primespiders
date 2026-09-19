from primespiders.url_filters import has_fragment, has_query, url_empty

from base import BaseSpider, EcommerceMixin
from components.bershka.url_filters import remove_static_page
from utils.operators import And, PartTest, Q, Rules


class Bershka(EcommerceMixin, BaseSpider):
    start_url: str | None = "https://www.bershka.com/"
    url_filters = (
        remove_static_page,
        url_empty,
        has_fragment,
        has_query,
    )

    async def run(self):
        await super().run()

    async def after_initial_navigation(self):
        # Cookie
        element = await self.page.wait_for_selector('#onetrust-banner-sdk', state='visible', timeout=10000)

        if element is not None:
            state = await self.page.query_selector(
                'button#onetrust-accept-btn-handler'
            )
            if state is not None:
                await state.click()

        language_modal = await self.page.wait_for_selector('.worldwide-actions', state='visible', timeout=10000)
        if language_modal is None:
            return
        
        # Language
        element = await language_modal.query_selector('.country-selection__wrapper')
        if element is not None:
            await element.click()

            input_field = await language_modal.query_selector('input[type="search"]')
            if input_field is not None:
                await input_field.fill("France")
                await input_field.press("Enter")

            save_button = await language_modal.query_selector('button[data-qa-anchor="saveLocation"]')
            if save_button is not None:
                await save_button.click()

    async def check_is_category_page(self, url):
        conditions = [
            Q(Rules.CONTAINS, "femmes"),
            Q(Rules.CONTAINS, "vetements"),
            PartTest(url, "celement", part='query')
        ]
        return And(url, *conditions)
