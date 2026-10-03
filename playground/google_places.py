import asyncio
from base64 import urlsafe_b64encode

from playwright.async_api import Error, async_playwright
from src.primespiders.components.google_maps.models import GooglePlaceModel
from src.primespiders.utils.urls import URL

STR_URL = 'https://www.google.com/maps/search/pharmacie+lille/@50.6192064,3.0031802,14z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI2MDkyOS4wIKXMDSoASAFQAw%3D%3D'

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

            feed_class = 'div[role="feed"]'
            await page.wait_for_selector(feed_class, state='visible')
            # feed = await page.query_selector(feed_class)

            stop_count: int = 0
            last_reference: str = ""

            must_load = True
            places: set[GooglePlaceModel] = set()

            while must_load:
                articles = await page.query_selector_all('div[role="article"]')
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

            await browser.close()

    asyncio.run(main())
