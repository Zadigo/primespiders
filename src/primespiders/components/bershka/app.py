import asyncio

from src.primespiders.base import BaseSpider, EcommerceMixin
from src.primespiders.components.bershka.models import ProductModel
from src.primespiders.components.bershka.url_filters import remove_static_page
from src.primespiders.url_filters import (
    has_fragment,
    has_query,
    ignore_social_media,
    url_empty,
)
from src.primespiders.utils import logger
from src.primespiders.utils.operators import And, Q, Rules


class Bershka(EcommerceMixin, BaseSpider):
    start_url: str | None = "https://www.bershka.com/fr/h-woman.html"

    @property
    def get_url_filters(self):
        return list(self.base_url_filters) + [
            remove_static_page,
            url_empty,
            has_fragment,
            has_query,
            ignore_social_media
        ]

    async def run(self, **kwargs):
        await super().run(**kwargs)

    async def on_page_actions(self, current_url, tg: asyncio.TaskGroup | None = None, **kwargs):
        if self.check_is_product_page(current_url):
            template = {
                'title': None,
                'unit_price': None,
                'sale_price': None,
                'available_sizes': [],
                'color': None,
                'reference': None,
                'product_images': [],
                'sizes': [],
                'url': None
            }

            info_block = await self.page.wait_for_selector('.product-detail-info')
            if info_block is not None:
                title = await info_block.query_selector('h1.product-title')
                if title is not None:
                    template['title'] = await title.text_content()

                unit_price = await info_block.query_selector('span[class^="current-price"]')
                if unit_price is not None:
                    text_content = await unit_price.text_content()
                    template['unit_price'] = float(text_content.replace('€', '').replace(',', '.'))

                size_buttons = await info_block.query_selector_all('button[class^="size-button"]')
                for item in size_buttons:
                    template['sizes'].append(await item.text_content())

                color = await info_block.query_selector('span[id="color-selector__name"]')
                if color is not None:
                    template['color'] = await color.text_content()

                reference = await info_block.query_selector('span[class^="color-selector__reference"]')
                if reference is not None:
                    template['reference'] = await reference.text_content()

                template['url'] = str(current_url)
                model = ProductModel(**template)
                self.signals.notify(current_url=current_url, product=model.model_dump())


    async def after_initial_navigation(self):
        # Cookie
        element = await self.page.wait_for_selector('#onetrust-banner-sdk', state='visible', timeout=10000)

        if element is not None:
            state = await self.page.query_selector(
                'button#onetrust-accept-btn-handler'
            )
            if state is not None:
                await state.click()

        try:
            language_modal = await self.page.wait_for_selector('.worldwide-actions', state='visible', timeout=10000)
        except Exception as e:
            logger.error(f"Error while waiting for language modal: {e}")
            return 
        else:
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
            Q(Rules.CONTAINS, "ticket-search"),
        ]
        return And(url, *conditions)
