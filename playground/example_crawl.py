import asyncio

from playwright.async_api import async_playwright

from primespiders.base import CrawlerSpider


class CrawlSpiderExample(CrawlerSpider):
    start_url = 'https://www.darjeeling.fr/'


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        example_spider = CrawlSpiderExample(page)
        await example_spider.run(browser)


if __name__ == '__main__':
    asyncio.run(main())
    