import asyncio
import datetime
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import pydantic

from src.primespiders.typings import TypeBaseSpider, TypeURL
from src.primespiders.utils import logger
from src.primespiders.utils.clients import get_postgres, get_redis


class PerformanceModel(pydantic.BaseModel):
    urls_to_visit_count: int = pydantic.Field(default=0)
    visited_urls_count: int = pydantic.Field(default=0)
    seen_urls_count: int = pydantic.Field(default=0)
    completion_pct: float = pydantic.Field(default=0.0)
    total_pct_urls_visited: float = pydantic.Field(default=0.0)
    last_seen_url: str | None = pydantic.Field(default=None)
    last_updated: str | None = pydantic.Field(default=None)


class BaseSignalsContainer(ABC):
    @abstractmethod
    def attach(self, observer: Observer) -> None:
        """
        Attach an observer to the subject.
        """

    @abstractmethod
    def detach(self, observer: Observer) -> None:
        """
        Detach an observer from the subject.
        """

    @abstractmethod
    async def notify(self, *, current_url: TypeURL, **kwargs: Any) -> None:
        """
        Notify all observers about an event.
        """


class SignalsContainer(BaseSignalsContainer):
    _observers: Sequence[Observer] = []

    def __init__(self, spider: TypeBaseSpider) -> None:
        self._spider = spider

    @property
    def count(self) -> int:
        return len(self._observers)

    def attach(self, observer: Observer) -> None:
        observer.spider = self._spider
        self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        self._observers = [obs for obs in self._observers if obs != observer]

    async def notify(self, *, current_url: TypeURL, **kwargs: Any) -> None:
        tasks: list[asyncio.Task] = []
        for observer in self._observers:
            tasks.append(asyncio.create_task(observer.update(current_url=current_url, **kwargs)))
        await asyncio.gather(*tasks)
                
    async def save_item(self, model: pydantic.BaseModel) -> str | None:
        """A simple implementation to save scrapped items to Redis 
        and notify observers about the saved item.
        
        Args:
            model (pydantic.BaseModel): The item model to be saved and notified about.
        """
        instance = get_redis()
        if instance is not None:
            storage_key = f"primespiders:{self._spider.job_uuid}:items"
            await instance.rpush(storage_key, model.model_dump())
            await self.notify(current_url=self._spider.start_url, item=model.model_dump())
            return storage_key


class Observer(ABC):
    def __init__(self) -> None:
        self.spider: TypeBaseSpider | None = None

    @abstractmethod
    async def update(self, **kwargs: Any) -> None:
        """Receive updates from SignalsContainer."""
        if self.spider is None:
            raise ValueError("Observer is not attached to any spider.")


class PerformanceObserver(Observer):
    """An observer that tracks the performance of the spider."""

    async def update(self, **kwargs) -> None:
        await super().update(**kwargs)

        redis_db = get_redis()
        if redis_db is not None:
            storage_key = f"primespiders:{self.spider.job_uuid}__performance"

            # Get the count of URLs to visit, visited URLs, and seen URLs
            urls_to_visit_count = redis_db.scard(self.spider.urls_to_visit_key)
            visited_urls_count = redis_db.scard(self.spider.visited_urls_key)
            seen_urls_count = redis_db.scard(self.spider.seen_urls_key)

            completion_pct = 0
            if urls_to_visit_count > 0:
                completion_pct = (
                    visited_urls_count / urls_to_visit_count
                ) * 100

            total_pct_urls_visited = 0
            if urls_to_visit_count > 0:
                total_pct_urls_visited = (
                    visited_urls_count / seen_urls_count
                ) * 100

            current_date = datetime.datetime.now(tz=datetime.UTC)
            # Check the started on timestamp and update if necessary
            started_on = redis_db.hget(storage_key, 'started_on')
            if started_on is None:
                redis_db.hset(storage_key, mapping={'started_on': str(current_date)})

            # template = {
            #     'urls_to_visit_count': urls_to_visit_count,
            #     'visited_urls_count': visited_urls_count,
            #     'seen_urls_count': seen_urls_count,
            #     'completion_pct': round(completion_pct, 2),
            #     'total_pct_urls_visited': round(total_pct_urls_visited, 2),
            #     'last_seen_url': str(kwargs.get('current_url', '')),
            #     'last_updated': str(current_date)
            # }
            
            model = PerformanceModel(
                urls_to_visit_count=urls_to_visit_count,
                visited_urls_count=visited_urls_count,
                seen_urls_count=seen_urls_count,
                completion_pct=round(completion_pct, 2),
                total_pct_urls_visited=round(total_pct_urls_visited, 2),
                last_seen_url=str(kwargs.get('current_url', '')),
                last_updated=str(current_date)
            )

            redis_db.hset(storage_key, mapping=model.model_dump())
            logger.info(f"Saved performance data. {model.completion_pct}% complete")

            # Send to Redis subscribers
            redis_db.publish(str(self.spider.job_uuid), str(model.model_dump()))

            other = json.dumps({
                'urls_to_visit': await self.spider.url_to_str(self.spider.urls_to_visit)
            })
            redis_db.publish(str(self.spider.job_uuid), other)
            logger.info(f"Published URLs to visit: {len(self.spider.urls_to_visit)} urls")



class HistoryObserver(Observer):
    """An observer that tracks the navigation history of the spider."""
    async def update(self, **kwargs: Any) -> None:
        pass


class PostgresGlobalObserver(Observer):
    """An observer that tracks the performance of the spider and 
    stores it in a PostgreSQL database."""

    CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS {name} ({columns})"

    def __init__(self):
        self.conn = get_postgres(dbname=self.database_name)
        self.tables = [
            {
                'name': 'performance',
                'columns': [
                    'urls_to_visit_count INTEGER',
                    'visited_urls_count INTEGER',
                    'seen_urls_count INTEGER',
                    'completion_pct FLOAT',
                    'total_pct_urls_visited FLOAT',
                    'last_seen_url TEXT',
                    'last_updated TIMESTAMP'
                ]
            }
        ]

        for table in self.tables:
            self.create_table(table)

    def __del__(self):
        if self.conn:
            self.conn.close()

    @staticmethod
    def finalize_sql(sql: str):
        return sql.strip().rstrip(';') + ';'

    def run_cursor(self, sql: str):
        with self.conn.cursor() as cursor:
            cursor.execute(self.finalize_sql(sql))
        self.conn.commit()

    def create_table(self, table):
        columns = ', '.join(table['columns'])
        create_table_sql = self.CREATE_TABLE_SQL.format(
            name=table['name'],
            columns=columns
        )

        self.run_cursor(create_table_sql)

    async def update(self, *, table: str | None = None, **kwargs: Any) -> None:
        if table is None:
            return
        
        columns = ', '.join([f"{col.split()[0]} = %s" for col in table['columns']])
        values = [
            kwargs.get('urls_to_visit_count', 0),
            kwargs.get('visited_urls_count', 0),
            kwargs.get('seen_urls_count', 0),
            kwargs.get('completion_pct', 0.0),
            kwargs.get('total_pct_urls_visited', 0.0),
            str(kwargs.get('last_seen_url', '')),
            str(kwargs.get('last_updated', ''))
        ]

        update_sql = self.finalize_sql(f"INSERT INTO {table['name']} SET {columns} VALUES ({', '.join(['%s'] * len(values))}")
        self.run_cursor(update_sql)
