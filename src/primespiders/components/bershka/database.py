from src.primespiders.backend.database import BaseDatabase


class BershkaDatabase(BaseDatabase):
    def create_tables(self):
        if self.conn is not None:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bershka_data (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    price NUMERIC NOT NULL,
                    url TEXT NOT NULL
                )
            """)
            self.conn.commit()
            cursor.close()
