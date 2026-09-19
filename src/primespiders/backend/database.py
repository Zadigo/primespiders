from abc import ABC, abstractmethod

from primespiders.utils.clients import get_postgres


class SQLMixin:
    CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS {name} ({columns})"

    @staticmethod
    def normalize_sql(value: str):
        return f"{value};" if not value.endswith(";") else value


class BaseDatabase(SQLMixin, ABC):
    database_name: str = ""

    def __init__(self):
        self.conn = get_postgres(dbname=self.database_name)

    @abstractmethod
    def create_tables(self):
        pass
