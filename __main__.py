import argparse
import asyncio
import inspect
from importlib import import_module

from playwright.async_api import async_playwright

from base import BaseSpider


async def main(app_name: str, headless: bool):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        # await app(page)

        try:
            mod = import_module(f'primespiders.components.{app_name}.app')
        except ModuleNotFoundError as e:
            print(f"Error importing module: {e}")
        else:
            candidate: type[BaseSpider] = None
            for _, klass in inspect.getmembers(mod, inspect.isclass):
                if issubclass(klass, BaseSpider):
                    candidate = klass

            if candidate is not None:
                instance = candidate(page)
                await instance.run()

        await browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a spider")

    parser.add_argument(
        "spider",
        type=str,
        help="The spider to run"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )

    args = parser.parse_args()
    asyncio.run(main(args.spider, headless=args.headless))
