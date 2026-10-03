from unittest.mock import AsyncMock, Mock, patch

import aiofiles
import pytest

from primespiders.observer import (
    HistoryCrawlObserver,
    PerformanceCrawlObserver,
    S3Observer,
    SignalsContainer,
)


def test_signals_container_initialization():
    container = SignalsContainer(None)
    performance_observer = PerformanceCrawlObserver()
    history_observer = HistoryCrawlObserver()

    container.attach(performance_observer)
    container.attach(history_observer)

    assert container.count == 2
    assert performance_observer in container._observers
    assert history_observer in container._observers


def test_signals_container_detachment():
    container = SignalsContainer(None)
    performance_observer = PerformanceCrawlObserver()
    history_observer = HistoryCrawlObserver()

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
        with patch('src.primespiders.observer.get_redis') as mget_redis:
            mget_redis.return_value.scard = Mock(return_value=0)
            mget_redis.return_value.hget = Mock(return_value=None)
            mget_redis.return_value.hset = Mock()

            observer = PerformanceCrawlObserver()
            assert observer is not None

            observer.spider = Mock(
                name='Spider',
                job_uuid='some_uuid',
                urls_to_visit_key="some_value",
                visited_urls_key="another_value",
                seen_urls_key="yet_another_value",
            )
            await observer.update(current_url="http://example.com")

    @pytest.mark.e2e
    async def test_save_data(self, base_spider):
        observer = PerformanceCrawlObserver()
        observer.spider = base_spider
        await observer.update()


class TestS3Observer:
    # async def test_initialization(self):
    #     with patch('src.primespiders.observer.boto3.Session') as msession:
    #         mclient = Mock()
    #         mresource = Mock()
    #         msession.return_value.client.return_value = mclient
    #         msession.return_value.resource.return_value = mresource

    #         from src.primespiders.observer import S3Observer
    #         observer = S3Observer()
    #         assert observer.client is mclient
    #         assert observer.bucket is mresource.Bucket.return_value

    @pytest.mark.e2e
    async def test_upload(self, tmp_path):
        test_file_path = tmp_path / 'test_file.txt'
        async with aiofiles.open(test_file_path, 'w') as f:
            await f.write('Test content')

            instance = S3Observer()
            await instance.update(
                file_content=b'Test content', 
                filename=test_file_path.name,
                file_key='rapports-cours-compte/test_file.txt'
            )

