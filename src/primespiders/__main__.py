import argparse
import asyncio
import inspect
import os
import pathlib
from importlib import import_module

from playwright.async_api import async_playwright

from src.primespiders.base import BaseSpider

BASE_DIR = pathlib.Path(__file__).parent.resolve()


async def main(app_name: str, headless: bool):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            downloads_path=BASE_DIR.joinpath("downloads"),
            timeout=60000,
        )

        page = await browser.new_page()
        await page.wait_for_selector('body')

        try:
            mod = import_module(f'src.primespiders.components.{app_name}.app')
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

    parser.add_argument(
        "--debug",
        type=str,
        help="The name of the app to run"
    )

    args = parser.parse_args()
    if args.debug:
        os.environ.setdefault("DEBUG", "True")

    asyncio.run(main(args.spider, headless=args.headless))
