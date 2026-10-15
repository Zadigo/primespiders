import argparse
import asyncio
import inspect
import os
import pathlib
import pkgutil
import threading
from importlib import import_module
from wsgiref.simple_server import WSGIServer

from playwright.async_api import async_playwright

from primespiders import components
from primespiders.base import BaseSpider
from primespiders.utils import logger

BASE_DIR = pathlib.Path(__file__).parent.resolve()

AVAILABLE = {m.name for m in pkgutil.iter_modules(components.__path__)}

GLOBAL_TASKS: list[asyncio.Task] = []

def shutdown_prometheus_server(wsgi_server: WSGIServer | None, thread: threading.Thread | None):
    def cancel_wrapper(task: asyncio.Task):
        if wsgi_server is not None:
            wsgi_server.shutdown()
            wsgi_server.server_close()

        if thread is not None:
            thread.join()

        GLOBAL_TASKS.remove(task)
    return cancel_wrapper


async def main(
    app_name: str, 
    with_id: str | None = None, 
    headless: bool = False, 
    ignore_queries: bool = True, 
    ignore_fragments: bool = True, 
    file: str | None = None,
    klass_name: str | None = None,
    tabs: int = 1
):
    async with async_playwright() as context:
        browser = await context.chromium.launch(
            headless=headless,
            downloads_path=BASE_DIR.joinpath("downloads"),
            timeout=60000,
        )

        page = await browser.new_page()
        if tabs > 1:
            for _ in range(tabs - 1):
                await browser.new_page()

        await page.wait_for_selector('body')

        try:
            mod = import_module(f'primespiders.components.{app_name}.app')
        except ModuleNotFoundError as e:
            await browser.close()
            logger.error("Cannot import component %r", e)
            raise
        except (TypeError, ValueError) as e:
            await browser.close()
            logger.error("Error importing component %r", e)
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
                    if klass_name is not None and klass.__name__.casefold() == klass_name.casefold():
                        candidate = klass
                        break
                    count += 1

            if count > 1 and klass_name is None:
                logger.error(
                    f"Multiple candidate classes found in module {mod.__name__}. "
                    "Please provide the --klass-name argument to choose a specific spider to run."
                )
                return

            if candidate is None:
                raise SystemExit(f"No suitable candidate class found in module {mod.__name__}")

            instance = candidate(page, with_id=with_id)

            if tabs > 1:
                instance.multi_tab_mode = True

            if with_id is not None:
                instance.job_uuid = with_id

            try:
                await instance.run(
                    browser=browser,
                    ignore_queries=ignore_queries,
                    ignore_fragments=ignore_fragments,
                )
            except (TypeError, ValueError) as e:
                await browser.close()
                raise ExceptionGroup("Error running spider", [e])

            # server_event = asyncio.Event()

            # _wsgi_server: WSGIServer = None
            # _thread: threading.Thread = None

            # async def run_prometheus_metrics():
            #     logger.info("Starting Prometheus metrics server on port 8000")
            #     await server_event.wait()
            #     wsgi_server, wsgi_thread = start_http_server(8000)  # exposes metrics at http://localhost:8000/metrics
            #     _wsgi_server, _thread = wsgi_server, wsgi_thread

            # async with asyncio.TaskGroup() as tg:
            #     t1 = tg.create_task(
            #         instance.run(
            #             browser=browser,
            #             ignore_queries=ignore_queries,
            #             ignore_fragments=ignore_fragments,
            #         )
            #     )

            #     t2 = tg.create_task(
            #         run_prometheus_metrics()
            #     )
                
            #     t1.add_done_callback(lambda t: GLOBAL_TASKS.remove(t))
            #     t2.add_done_callback(shutdown_prometheus_server(_wsgi_server, _thread))

            #     GLOBAL_TASKS.extend([t1, t2])

            #     if not t1.cancelled():
            #         server_event.set()
            
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
    parser.add_argument(
        "--tabs",
        type=int,
        default=1,
        help="Specify the number of tabs to open"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the cache before running the spider"
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=1,
        help="Number of sessions to use"
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
                file=args.file,
                klass_name=args.klass_name,
                tabs=args.tabs,
            )
        )
    except KeyboardInterrupt:
        logger.error("Spider execution interrupted by user.")
