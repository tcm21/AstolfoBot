import os
import psycopg2
import configparser

DATABASE_URL = os.environ.get("DATABASE_URL")
parser = configparser.ConfigParser()
if not DATABASE_URL:
    parser.read('env.config')
    DATABASE_URL = parser.get('Auth', 'DATABASE_URL')


def init_region_db():
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS regions(guild_id BIGINT PRIMARY KEY, region VARCHAR(2))')


def set_region(guild_id: int, region: str):
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        cur = conn.cursor()
        cur.execute(f'INSERT INTO regions(guild_id, region) values({guild_id}, \'{region}\') ON CONFLICT (guild_id) DO UPDATE SET region=\'{region}\'')
        conn.commit()


def get_region(guild_id: int):
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT region FROM regions WHERE guild_id = {guild_id}')
        row = cur.fetchone()
        if row:
            return row[0]
    return None
