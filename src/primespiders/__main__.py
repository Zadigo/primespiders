import argparse
import asyncio
import inspect
import os
import pathlib
from importlib import import_module

from playwright.async_api import async_playwright

from src.primespiders.base import BaseSpider
from src.primespiders.utils import logger

BASE_DIR = pathlib.Path(__file__).parent.resolve()


async def main(app_name: str, with_id: str | None = None, headless: bool = False, ignore_queries: bool = True, ignore_fragments: bool = True):
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
            logger.error(f"Error importing module: {e}")
        else:
            candidate: type[BaseSpider] = None
            for _, klass in inspect.getmembers(mod, inspect.isclass):
                if issubclass(klass, BaseSpider):
                    candidate = klass

            if candidate is not None:
                instance = candidate(page, with_id=with_id)

                if with_id is not None:
                    instance.job_uuid = with_id

                try:
                    await instance.run(
                        ignore_queries=ignore_queries,
                        ignore_fragments=ignore_fragments,
                    )
                except KeyboardInterrupt:
                    logger.error("Spider execution interrupted by user.")
                except Exception as e:
                    raise ExceptionGroup("Error running spider", [e])
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

    parser.add_argument(
        "--ignore-queries",
        action="store_true",
        default=True,
        help="Ignore urls with query parameters when crawling"
    )

    parser.add_argument(
        "--ignore-fragments",
        action="store_true",
        default=True,
        help="Ignore urls with URL fragments when crawling"
    )

    parser.add_argument(
        "--with-id",
        type=str,
        help="Start a spider that was previously run with the specified ID"
    )

    args = parser.parse_args()
    if args.debug:
        os.environ.setdefault("DEBUG", "True")

    asyncio.run(
        main(
            args.spider,
            with_id=args.with_id,
            headless=args.headless, 
            ignore_queries=args.ignore_queries,
            ignore_fragments=args.ignore_fragments
        )
    )
