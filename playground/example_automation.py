import asyncio

from playwright.async_api import async_playwright

from primespiders.base import AutomationSpider


class AutomationSpiderExample(AutomationSpider):
    start_url = 'https://www.darjeeling.fr/'


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            timeout=60000,
        )
        page = await browser.new_page()
        
        example_spider = AutomationSpiderExample(page)
        await example_spider.run(browser)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt as e:
        print(f"An error occurred: {e}")
    