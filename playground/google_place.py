import asyncio
import re

from playwright.async_api import ElementHandle, Error, Page, async_playwright

from primespiders.components.google_maps.models import (
    GoogleAdvancedPlaceModel,
    GoogleReviewModel,
)
from primespiders.utils import logger

STR_URL = 'https://www.google.com/maps/place/Lillenium/@50.6155448,3.0454505,17z/data=!4m16!1m9!3m8!1s0x47c2d50a449ffe6b:0x96f45b11c697549d!2sLillenium!8m2!3d50.6155448!4d3.0480254!9m1!1b1!16s%2Fg%2F11f55_9f9k!3m5!1s0x47c2d50a449ffe6b:0x96f45b11c697549d!8m2!3d50.6155448!4d3.0480254!16s%2Fg%2F11f55_9f9k?entry=ttu&g_ep=EgoyMDI2MDkzMC4wIKXMDSoASAFQAw%3D%3D'


async def get_title(main_panel: ElementHandle, model: GoogleAdvancedPlaceModel):
    try:
        title_loc = await main_panel.query_selector('h1')
        if title_loc is not None:
            model.name = await title_loc.inner_text()
    except Error as e:
       logger.error(f"Error getting title: {e}")
    except (TypeError, ValueError, AttributeError) as e:
        logger.error(f"Unexpected error getting title: {e}")


async def get_rating(page: Page, model: GoogleAdvancedPlaceModel):
    try:
        rating_loc = page.get_by_label(re.compile(r"\d\,\d\s?étoiles$", re.IGNORECASE))
        if rating_loc is not None:
            str_result = await rating_loc.get_attribute('aria-label')
            str_value, _ = str_result.replace('\xa0', ' ').split(' ')
            model.rating = float(str_value.replace(',', '.'))
    except Error as e:
        logger.error(f"Error getting rating: {e}")
    except (TypeError, ValueError, AttributeError) as e:
        logger.error(f"Unexpected error getting rating: {e}")


async def get_category(main_panel: ElementHandle, model: GoogleAdvancedPlaceModel):
    try:
        handle = await main_panel.query_selector('button[jsaction$="category"]')
        if handle is not None:
            model.category = await handle.inner_text()
    except Error as e:
        logger.error(f"Error getting category: {e}")
    except (TypeError, ValueError, AttributeError) as e:
        logger.error(f"Unexpected error getting category: {e}")


async def get_metadata(page: Page, model: GoogleAdvancedPlaceModel):
    try:
        aria_labels = ['Adresse:', 'Site Web:', 'Numéro de téléphone:']
        for label in aria_labels:
            loc = page.get_by_label(re.compile(rf"^{label}", re.IGNORECASE))
            if loc is not None:
                result = await loc.get_attribute('aria-label') or ''
                clean_result = result.removeprefix(label).strip()

                match label:
                    case 'Adresse:':
                        model.address = clean_result
                    case 'Site Web:':
                        model.website = clean_result
                    case 'Numéro de téléphone:':
                        model.phone_number = clean_result
    except Error as e:
        logger.error(f"Error getting metadata: {e}")
    except (TypeError, ValueError, AttributeError) as e:
        logger.error(f"Unexpected error getting metadata: {e}")


async def parse_review(review: ElementHandle, model: GoogleAdvancedPlaceModel):
    try:
        review_model = GoogleReviewModel()

        author_loc = await review.get_attribute('aria-label')
        if author_loc is not None:
            review_model.author_name = author_loc

        review_id_loc = await review.get_attribute('data-review-id')
        if review_id_loc is not None:
            review_model.review_id = review_id_loc

        see_more_button = await review.query_selector('button[aria-label="Voir plus"]')
        if see_more_button is not None:
            await see_more_button.click(button='left')

        await asyncio.sleep(1)

        text_loc = await review.query_selector('div[class="MyEned"][lang]')
        if text_loc is not None:
            review_model.text = await text_loc.inner_text()

        # data_href_button = await review.query_selector('button[data-href]')
        # if data_href_button is not None:
        #     div_locs = await data_href_button.query_selector_all('div')
        #     last_div = div_locs[-1]
        #     if last_div is not None:
        #         pass

        model.reviews.append(review_model)
    except Error as e:
        logger.error(f"Error parsing review: {e}")
    except (TypeError, ValueError, AttributeError) as e:
        logger.error(f"Unexpected error parsing review: {e}")


if __name__ == "__main__":
    async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            await page.goto(STR_URL)

            # 1. Click the "Tout accepter" button if it exists
            await page.wait_for_selector('body')
            buttons = await page.query_selector_all('button')
            for button in buttons:
                text = await button.inner_text()
                if text.strip().lower() == "tout accepter":
                    try:
                        await button.click(button='left')
                    except Error as e:
                        print(f"Error clicking 'Tout accepter' button: {e}")
                    break

            await page.wait_for_event('load')

            await page.wait_for_selector('div[role="main"]', timeout=10000)
            main_panel = await page.query_selector('div[role="main"]')

            if main_panel is not None:
                model = GoogleAdvancedPlaceModel()
                model.url = page.url

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(get_title(main_panel, model))
                    tg.create_task(get_rating(page, model))
                    tg.create_task(get_category(main_panel, model))
                    tg.create_task(get_metadata(page, model))

                # 2. Go to the review tab
                await asyncio.sleep(1)

                tabs = await page.query_selector_all('button[role="tab"]')
                reviews_tab = tabs[1]
                await reviews_tab.click(button='left')

                # sort_button_loc = page.get_by_label('Trier les avis')
                # if sort_button_loc is not None:
                #     await sort_button_loc.click(button='left')
                await asyncio.sleep(1)
                reviews = await page.query_selector_all('div[data-review-id]')

                for review in reviews:
                    await parse_review(review, model)

                # async with asyncio.Lock():
                #     for review in reviews:
                #         await parse_review(review, model)

                #         # review_model = GoogleReviewModel()

                #         # author_loc = await review.get_attribute('aria-label')
                #         # if author_loc is not None:
                #         #     review_model.author_name = author_loc

                #         # review_id_loc = await review.get_attribute('data-review-id')
                #         # if review_id_loc is not None:
                #         #     review_model.review_id = review_id_loc

                #         # see_more_button = await review.query_selector('button[aria-label="Voir plus"]')
                #         # if see_more_button is not None:
                #         #     await see_more_button.click(button='left')

                #         # data_href_button = await review.query_selector('button[data-href]')
                #         # if data_href_button is not None:
                #         #     div_locs = await data_href_button.query_selector_all('div')
                #         #     last_div = div_locs[-1]
                #         #     if last_div is not None:
                #         #         pass

                #         # await asyncio.sleep(1)

                #         # text_loc = await review.query_selector('div[class="MyEned"][lang]')
                #         # if text_loc is not None:
                #         #     review_model.text = await text_loc.inner_text()
                #         # model.reviews.append(review_model)

                #         # await asyncio.sleep(1)

                if reviews:
                    last_review = reviews[-1]
                    await last_review.evaluate('element => element.scrollIntoView()')
                    await asyncio.sleep(1)


                # title_loc = await main_panel.query_selector('h1')
                # if title_loc is not None:
                #     title = await title_loc.inner_text()

                # rating_loc = page.get_by_label(re.compile(r"\d\,\d\s?étoiles$", re.IGNORECASE))
                # if rating_loc is not None:
                #     rating = await rating_loc.get_attribute('aria-label')

                # # rating_loc = page.get_by_label(re.compile(r"\d.*avis$", re.IGNORECASE))
                # # if rating_loc is not None:
                # #     number_of_reviews = await rating_loc.inner_text()

                # place_type_loc = await page.query_selector('button[jsaction$="category"]')
                # if place_type_loc is not None:
                #     place_type = await place_type_loc.inner_text()

                # aria_labels = ['Adresse:', 'Site Web:', 'Numéro de téléphone:']
                # for label in aria_labels:
                #     loc = page.get_by_label(re.compile(rf"^{label}", re.IGNORECASE))
                #     if loc is not None:
                #         result = await loc.get_attribute('aria-label') or ''
                #         clean_result = result.removeprefix(label).strip()
                #         if label == 'Adresse:':
                #             address = clean_result
                #         elif label == 'Site Web:':
                #             website = clean_result
                #         elif label == 'Numéro de téléphone:':
                #             phone_number = clean_result


            while True:
                pass

        await browser.close()

    asyncio.run(main())
