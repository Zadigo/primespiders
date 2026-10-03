from typing import Any

from primespiders.components.google_maps.models import GooglePlaceModel
from primespiders.observer import Observer, PostgresMixin, get_postgres
from primespiders.utils import DB_NAME


class PostgresGooglePlaceObserver(PostgresMixin, Observer):
    def __init__(self):
        super().__init__()
        self.conn = get_postgres(dbname=DB_NAME)
        self.tables = [
            {
                'name': 'google_place',
                'columns': [
                    'reference TEXT',
                    'data JSONB'
                ]
            }
        ]

        for table in self.tables:
            self.create_table(table)

    async def update(self, place: GooglePlaceModel, **kwargs: Any):
        pass
