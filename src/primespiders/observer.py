import asyncio
import datetime
import io
import json
import mimetypes
import pathlib
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import aiofiles
import boto3
import pydantic
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from primespiders.typings import TypeBaseSpider, TypeURL
from primespiders.utils import DB_NAME, ENV, logger
from primespiders.utils.clients import get_postgres, get_redis


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
    async def notify(self, *, current_url: TypeURL | None = None, tag: str | None = None, **kwargs: Any) -> None:
        """
        Notify all observers about an event, optionally filtered by tag.
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

    async def notify(self, *, current_url: TypeURL | None = None, tag: str | None = None, **kwargs: Any) -> None:
        tasks: list[asyncio.Task] = []
        for observer in self._observers:
            if tag is not None and observer.tag != tag:
                continue
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
    tag: str | None = None

    def __init__(self) -> None:
        self.spider: TypeBaseSpider | None = None

    @abstractmethod
    async def update(self, **kwargs: Any) -> None:
        """Receive updates from SignalsContainer."""
        if self.spider is None:
            raise ValueError("Observer is not attached to any spider.")


class PerformanceCrawlObserver(Observer):
    """An observer that tracks the performance of the spider."""

    tag = 'performance'

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


class HistoryCrawlObserver(Observer):
    """An observer that tracks the navigation history of the spider."""

    tag = 'history'

    async def update(self, **kwargs: Any) -> None:
        pass


class PostgresMixin:
    CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS {name} ({columns})"

    def __init__(self):
        self.conn = get_postgres(dbname=DB_NAME)
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


class PostgresCrawlObserver(PostgresMixin,Observer):
    """An observer that tracks the performance of the spider and 
    stores it in a PostgreSQL database."""

    tag = 'postgres'

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


class RedisChannelObserver(Observer):
    """An observer that publishes updates to a Redis channel."""

    tag = 'redis'

    def __init__(self):
        super().__init__()

    async def update(self, **kwargs: Any) -> None:
        if self.spider.redis_client is not None:
            clean_values: dict = {}
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_values[key] = value
                    continue

                if isinstance(value, uuid.UUID):
                    clean_values[key] = str(value)
                    continue

                if isinstance(value, pydantic.BaseModel):
                    clean_values[key] = value.model_dump()
                    continue

            self.spider.redis_client.publish(
                f'primespiders__{self.spider.job_uuid}', 
                json.dumps(clean_values)
            )


class S3Observer(Observer):
    """An observer that uploads/updates to an S3 bucket."""

    tag = 's3'

    def __init__(self):
        super().__init__()

        self.AWS_S3_ACCESS_KEY_ID: str | None = ENV.string('AWS_S3_ACCESS_KEY_ID')
        self.AWS_S3_SECRET_ACCESS_KEY: str | None = ENV.string('AWS_S3_SECRET_ACCESS_KEY')
        self.AWS_STORAGE_BUCKET_NAME: str | None = ENV.string('AWS_STORAGE_BUCKET_NAME')
        self.AWS_S3_REGION_NAME: str | None = ENV.string('AWS_S3_REGION_NAME')

        session_config = {
            'aws_access_key_id': self.AWS_S3_ACCESS_KEY_ID,
            'aws_secret_access_key': self.AWS_S3_SECRET_ACCESS_KEY,
        }

        if self.AWS_S3_REGION_NAME:
            session_config['region_name'] = self.AWS_S3_REGION_NAME

        session = boto3.Session(**session_config)

        client_config = {}
        client = session.client('s3', **client_config)
        resource = session.resource('s3', **client_config)

        # This is a trap because if always returns an object
        # even if the bucket does not exist. We need to explicitly
        # test if the bucket exists by calling head_bucket -- see below
        bucket = resource.Bucket(self.AWS_STORAGE_BUCKET_NAME)

        try:
                
            client.head_bucket(Bucket=self.AWS_STORAGE_BUCKET_NAME)
            logger.info(f"✓ Connected to existing bucket: {self.AWS_STORAGE_BUCKET_NAME}")
        except ClientError as e:
            # If the bucket does not exist we receive
            # a 404 code and that will be the trigger
            # that will be using to create a new bucket
            error_code = e.response['Error']['Code']

            if error_code == '404':
                logger.info(
                    f"Bucket {self.AWS_STORAGE_BUCKET_NAME} "
                    "not found. Attempting to create..."
                )

                try:
                    create_bucket_config = {}

                    # For regions other than us-east-1, we need to specify LocationConstraint
                    if self.AWS_S3_REGION_NAME and self.AWS_S3_REGION_NAME != 'us-east-1':
                        create_bucket_config['CreateBucketConfiguration'] = {
                            'LocationConstraint': self.AWS_S3_REGION_NAME
                        }

                    client.create_bucket(
                        Bucket=self.AWS_STORAGE_BUCKET_NAME,
                        **create_bucket_config
                    )

                    waiter = client.get_waiter('bucket_exists')
                    waiter.wait(
                        Bucket=self.AWS_STORAGE_BUCKET_NAME,
                        WaiterConfig={'Delay': 2, 'MaxAttempts': 30}
                    )

                    logger.info(f"✓ Created bucket: {self.AWS_STORAGE_BUCKET_NAME}")
                except ClientError as creation_error:
                    raise TypeError(
                        f"Failed to create bucket '{self.AWS_STORAGE_BUCKET_NAME}': "
                        f"{creation_error.response['Error']['Message']}"
                    )
            elif error_code == '403':
                raise TypeError(
                    f"Access denied to bucket '{self.AWS_STORAGE_BUCKET_NAME}'. "
                    f"Check your AWS credentials and bucket permissions."
                )
            else:
                raise TypeError(
                    f"Failed to access bucket '{self.AWS_STORAGE_BUCKET_NAME}': "
                    f"{e.response['Error']['Message']}"
                )

        logger.info(f"Uploads will go to bucket: {bucket.name}")

        self.client = client
        self.bucket = bucket

        self.upload_count = 0
        self.uploaded_files: list[str] = []

    async def update(self, **kwargs: Any) -> None:
        file_content: bytes = kwargs.get('file_content')
        if not isinstance(file_content, (bytes, bytearray, io.BytesIO)):
            logger.error("file_content must be of type bytes")
            return

        if isinstance(file_content, io.BytesIO):
            buffer = file_content
        else:
            buffer = io.BytesIO(file_content)

        file_key: str = kwargs.get('file_key')
        content_type = mimetypes.guess_type(file_key)[0]

        extra_args = {'ContentType': content_type or 'application/octet-stream'}
        extra_args.update(ACL='public-read')

        try:
            self.client.upload_fileobj(
                Fileobj=buffer,
                Bucket=self.AWS_STORAGE_BUCKET_NAME,
                Key=file_key,
                ExtraArgs=extra_args
            )
        except ClientError as e:
            logger.error(f"Failed to upload file: {file_key}. Error: {e!s}")
        except (NoCredentialsError, BotoCoreError) as e:
            logger.error(str(e))
            raise
        else:
            self.upload_count += 1
            self.uploaded_files.append(file_key)
            logger.info(f"OK Uploaded {file_key}")


class JsonFileObserver(Observer):
    """A JSON file observer that writes data to a JSON file asynchronously."""

    tag = 'json'

    def __init__(self, filename: str, base_path: pathlib.Path | None = None):
        super().__init__()

        fullpath = base_path or pathlib.Path(__file__).parent.absolute()
        self.filepath = fullpath / 'data' / filename
        
        self.template: dict[str, Any] = {
            'created_at': datetime.utcnow().isoformat(),
            'timestamp': datetime.utcnow().isoformat(),
            'results': []
        }

    async def update(self, **kwargs: Any) -> None:
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

        self.template['timestamp'] = datetime.utcnow().isoformat()

        async with asyncio.Lock(), aiofiles.open(self.filepath, 'w+') as f:
            existing_data = await f.read()
            if existing_data:
                self.template['results'] = json.loads(existing_data)

            data: dict[str, Any] | list[dict[str, Any]] = kwargs.get('data')
            if isinstance(data, list):
                self.template['results'].extend(data)
            else:
                self.template['results'].append(data)
            await f.write(json.dumps(self.template, ensure_ascii=False, indent=4))
        
        logger.info(f"OK Written {self.filepath}")
