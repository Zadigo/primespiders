from unittest.mock import AsyncMock, Mock, patch

from primespiders.observer import HistoryObserver, PerformanceObserver, SignalsContainer


def test_signals_container_initialization():
    container = SignalsContainer(None)
    performance_observer = PerformanceObserver()
    history_observer = HistoryObserver()

    container.attach(performance_observer)
    container.attach(history_observer)

    assert container.count == 2
    assert performance_observer in container._observers
    assert history_observer in container._observers


def test_signals_container_detachment():
    container = SignalsContainer(None)
    performance_observer = PerformanceObserver()
    history_observer = HistoryObserver()

    container.attach(performance_observer)
    container.attach(history_observer)

    container.detach(performance_observer)

    assert container.count == 1
    assert performance_observer not in container._observers
    assert history_observer in container._observers


async def test_signals_container_notification():
    container = SignalsContainer(None)
    mocked_observer = Mock()
    mocked_observer.update = AsyncMock()

    container.attach(mocked_observer)
    await container.notify(current_url="http://example.com")

    mocked_observer.update.assert_called_once_with(
        current_url="http://example.com"
    )


class TestPerformanceObserver:
    async def test_initialization(self):
        with patch('primespiders.observer.get_redis') as mget_redis:
            mget_redis.return_value.scard = Mock(return_value=0)
            mget_redis.return_value.hget = Mock(return_value=None)
            mget_redis.return_value.hset = Mock()

            observer = PerformanceObserver()
            assert observer is not None

            observer.spider = Mock(
                name='Spider',
                job_uuid='some_uuid',
                urls_to_visit_key="some_value",
                visited_urls_key="another_value",
                seen_urls_key="yet_another_value",
            )
            await observer.update(current_url="http://example.com")
