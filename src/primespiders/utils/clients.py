import os

import psycopg2
import redis

from src.primespiders.utils import logger


def get_redis():
    client = redis.Redis(host='localhost', port=6379, db=0)
    try:
        client.ping()
    except redis.ConnectionError:
        logger.error("Failed to connect to Redis")
        return None
    else:
        return client


def get_postgres(**kwargs: str):
    """Get a PostgreSQL connection.

    Keyword Args:
        dbname (str): Database name. Defaults to environment variable POSTGRES_DB.
        user (str): Database user. Defaults to environment variable POSTGRES_USER.
        password (str): Database password. Defaults to environment variable POSTGRES_PASSWORD.
        host (str): Database host. Defaults to 'localhost'.
        port (str): Database port. Defaults to '5432'.

    Returns:
        psycopg2.extensions.connection: PostgreSQL connection object or None if connection fails.
    """
    try:
        conn = psycopg2.connect(
            dbname=kwargs.get("dbname", os.getenv("POSTGRES_DB")),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=kwargs.get("host", "localhost"),
            port=kwargs.get("port", "5432")
        )
    except psycopg2.OperationalError as e:
        logger.error(f"- Failed to connect to PostgreSQL: {e}")
        return None
    else:
        return conn
