import datetime
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from src.primespiders.typings import TypeBaseSpider, TypeURL
from src.primespiders.utils.clients import get_redis


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
        for observer in self._observers:
            await observer.update(current_url=current_url, **kwargs)

    # async def some_business_logic(self) -> None:
    #     await self.notify(current_url=self._spider.start_url)


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
            storage_key = f"primespiders:{self.spider.job_uuid}"

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

            # Check the started on timestamp and update if necessary
            started_on = redis_db.hget(storage_key, 'started_on')
            if started_on is None:
                d = str(datetime.datetime.now(tz=datetime.UTC))
                redis_db.hset(
                    storage_key,
                    'performance',
                    mapping={'started_on': d}
                )

            template = {
                'urls_to_visit_count': urls_to_visit_count,
                'visited_urls_count': visited_urls_count,
                'seen_urls_count': seen_urls_count,
                'completion_pct': completion_pct,
                'total_pct_urls_visited': total_pct_urls_visited,
                'last_seen_url': str(kwargs.get('current_url', '')),
                'last_updated': str(datetime.datetime.now(tz=datetime.UTC))
            }

            redis_db.hset(storage_key, 'performance', mapping=template)

            # Send to Redis subscribers
            redis_db.publish(str(self.spider.job_uuid), str(template))
            redis_db.publish(str(self.spider.job_uuid), {
                'utls_to_vists': self.spider.urls_to_visit
            })


class HistoryObserver(Observer):
    async def update(self, **kwargs: Any) -> None:
        pass
