import sqlite3

DB_NAME = 'data.db'
def init_region_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS regions(guild_id INTEGER PRIMARY KEY, region STRING)')


def set_region(guild_id: int, region: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(f'INSERT OR REPLACE INTO regions(guild_id, region) values({guild_id}, "{region}")')
        conn.commit()


def get_region(guild_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(f'SELECT region FROM regions WHERE guild_id = {guild_id}')
        for row in cursor:
            return row[0]
    return None
