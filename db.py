import os
import psycopg2
from psycopg2.extras import execute_values
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


def init_optimized_quests_db():
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS optimized_quests
            (
                master_mission_id bigint NOT NULL,
                quest_id bigint NOT NULL,
                target_id character varying NOT NULL,
                target_count bigint NOT NULL,
                region character varying(2),
                "count" bigint NOT NULL,
                CONSTRAINT optimized_quests_pkey PRIMARY KEY (master_mission_id, quest_id, target_id)
            )
            """)


class OptimizedDrop:
    master_mission_id: int
    quest_id: int
    target_id: str
    target_count: int
    count: int

    def __init__(self, master_mission_id, quest_id, target_id, target_count, count):
        self.master_mission_id = master_mission_id
        self.quest_id = quest_id
        self.target_id = target_id
        self.target_count = target_count
        self.count = count


def populate_drop_data(drops: list[OptimizedDrop], region: str = "JP"):
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        cur = conn.cursor()
        sql = f"DELETE FROM optimized_quests WHERE region='{region}';"
        cur.execute(sql)
        sql = "INSERT INTO optimized_quests(master_mission_id, quest_id, target_id, target_count, count, region) VALUES %s"
        execute_values(
            cur,
            sql,
            [(drop.master_mission_id, drop.quest_id, drop.target_id, drop.target_count, drop.count, region) for drop in drops]
        )
        conn.commit()


def get_drop_data(master_mission_id: int, region: str = "JP"):
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT master_mission_id, quest_id, target_id, target_count, count FROM optimized_quests WHERE master_mission_id = {master_mission_id} and region = \'{region}\' ORDER BY quest_id')
        if cur.rowcount > 0:
            return [OptimizedDrop(row[0], row[1], row[2], row[3], row[4]) for row in cur.fetchall()]
        return None