import argparse
import asyncio
import inspect
import os
import pathlib
import pkgutil
from importlib import import_module

from playwright.async_api import async_playwright

from primespiders import components
from primespiders.base import BaseSpider
from primespiders.utils import logger

BASE_DIR = pathlib.Path(__file__).parent.resolve()

AVAILABLE = {m.name for m in pkgutil.iter_modules(components.__path__)}

async def main(
    app_name: str, 
    with_id: str | None = None, 
    headless: bool = False, 
    ignore_queries: bool = True, 
    ignore_fragments: bool = True, 
    automate: bool = False, 
    file: str | None = None,
    klass_name: str | None = None
):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            downloads_path=BASE_DIR.joinpath("downloads"),
            timeout=60000,
        )

        page = await browser.new_page()
        await page.wait_for_selector('body')

        try:
            mod = import_module(f'primespiders.components.{app_name}.app')
        except ModuleNotFoundError as e:
            await browser.close()
            logger.error("Cannot import component %r", e)
            raise
        else:
            if app_name not in AVAILABLE:
                raise SystemExit(f"Unknown component {app_name!r}. Available: {sorted(AVAILABLE)}")

            count: int = 0
            candidate: type[BaseSpider] = None
            klasses = inspect.getmembers(mod, inspect.isclass)
            for _, klass in klasses:
                if issubclass(klass, BaseSpider):
                    candidate = klass
                    count += 1

            if count > 1 and klass_name is None:
                logger.error(
                    f"Multiple candidate classes found in module {mod.__name__}. "
                    "Please provide the --klass-name argument to choose a specific spider to run."
                )
                return
            else:
                if klass_name is not None:
                    for _, klass in klasses:
                        if issubclass(klass, BaseSpider) and klass.__name__.casefold() == klass_name.casefold():
                            candidate = klass
                            break

            if candidate is not None:
                instance = candidate(page, with_id=with_id, automation=automate)

                if with_id is not None:
                    instance.job_uuid = with_id

                try:
                    await instance.run(
                        ignore_queries=ignore_queries,
                        ignore_fragments=ignore_fragments,
                    )
                except (TypeError, ValueError) as e:
                    await browser.close()
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

    parser.add_argument(
        "--automate",
        action="store_true",
        default=False,
        help="Run automation on a page without crawling"
    )

    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Specify a file to use for automation"
    )

    parser.add_argument(
        "--klass-name",
        type=str,
        default=None,
        help="Specify a spider class to run when the app module contains multiple spider options"
    )

    args = parser.parse_args()
    if args.debug:
        os.environ.setdefault("DEBUG", "True")

    try:
        asyncio.run(
            main(
                args.spider,
                with_id=args.with_id,
                headless=args.headless, 
                ignore_queries=args.ignore_queries,
                ignore_fragments=args.ignore_fragments,
                automate=args.automate,
                file=args.file,
                klass_name=args.klass_name,
            )
        )
    except KeyboardInterrupt:
        logger.error("Spider execution interrupted by user.")
