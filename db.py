import os
import psycopg2
from psycopg2.extras import execute_values
import configparser
import fgo_api_types.nice as nice
from collections import Counter


DATABASE_URL = os.environ.get("DATABASE_URL")
parser = configparser.ConfigParser()
if not DATABASE_URL:
    parser.read('env.config')
    DATABASE_URL = parser.get('Auth', 'DATABASE_URL')


def init_region_db():
    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS regions(guild_id BIGINT PRIMARY KEY, region VARCHAR(2))')


def set_region(guild_id: int, region: str):
    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        cur.execute(f'INSERT INTO regions(guild_id, region) values({guild_id}, \'{region}\') ON CONFLICT (guild_id) DO UPDATE SET region=\'{region}\'')
        conn.commit()


def get_region(guild_id: int):
    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT region FROM regions WHERE guild_id = {guild_id}')
        row = cur.fetchone()
        if row:
            return row[0]
    return None


def init_optimized_quests_db():
    with psycopg2.connect(DATABASE_URL) as conn:
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
                is_or boolean NOT NULL DEFAULT false,
                CONSTRAINT optimized_quests_pkey PRIMARY KEY (master_mission_id, quest_id, target_id)
            )
            """)


class OptimizedQuest:
    master_mission_id: int
    quest_id: int
    target_id: str
    target_count: int
    count: int
    is_or: bool

    def __init__(self, master_mission_id, quest_id, target_id, target_count, count, is_or):
        self.master_mission_id = master_mission_id
        self.quest_id = quest_id
        self.target_id = target_id
        self.target_count = target_count
        self.count = count
        self.is_or = is_or


def insert_optimized_quests(drops: list[OptimizedQuest], region: str = "JP"):
    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        sql = f"DELETE FROM optimized_quests WHERE region='{region}';"
        cur.execute(sql)
        sql = "INSERT INTO optimized_quests(master_mission_id, quest_id, target_id, target_count, count, is_or, region) VALUES %s"
        execute_values(
            cur,
            sql,
            [(drop.master_mission_id, drop.quest_id, drop.target_id, drop.target_count, drop.count, drop.is_or, region) for drop in drops]
        )
        conn.commit()


def get_optimized_quests(master_mission_id: int, region: str = "JP"):
    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT master_mission_id, quest_id, target_id, target_count, count, is_or FROM optimized_quests WHERE master_mission_id = {master_mission_id} and region = \'{region}\' ORDER BY quest_id')
        if cur.rowcount > 0:
            return [OptimizedQuest(row[0], row[1], row[2], row[3], row[4], row[5]) for row in cur.fetchall()]
        return None


def insert_quest_enemies(quest_id: int, enemies: list[nice.QuestEnemy]):
    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        enemy_counts = Counter(enemy.svt.id for enemy in enemies)
        sql = """
        INSERT INTO quest_enemies(quest_id, enemy_id, enemy_count) VALUES %s
        ON CONFLICT (quest_id, enemy_id) DO UPDATE SET
        (quest_id, enemy_id, enemy_count) = (EXCLUDED.quest_id, EXCLUDED.enemy_id, EXCLUDED.enemy_count)
        """
        execute_values(
            cur,
            sql,
            [(quest_id, enemy_id, enemy_count) for enemy_id, enemy_count in enemy_counts.items()]
        )
        for enemy in enemies:
            sql = "INSERT INTO enemy_traits(enemy_id, trait_id) VALUES %s ON CONFLICT (enemy_id, trait_id) DO NOTHING"
            execute_values(
                cur,
                sql,
                [(enemy.svt.id, trait.id) for trait in enemy.traits]
            )
        conn.commit()


class QuestEnemiesTraits:
    quest_id: int
    enemy_id: str
    count: int
    traits: list[int]

    def __init__(self, quest_id, enemy_id, count, traits):
        self.quest_id = quest_id
        self.enemy_id = enemy_id
        self.count = count
        self.traits = traits


def get_quest_enemies(quest_id: int) -> list[QuestEnemiesTraits]:
    with psycopg2.connect(DATABASE_URL) as conn:
        cur = conn.cursor()
        cur.execute(f"""
        SELECT quest_id, quest_enemies.enemy_id, enemy_count, trait_id
        FROM quest_enemies
        INNER JOIN enemy_traits ON
            quest_enemies.enemy_id = enemy_traits.enemy_id
        WHERE quest_id = {quest_id}
        ORDER BY quest_id, enemy_id, enemy_count
        """)
        if cur.rowcount <= 0:
            return None
            
        quest_id = None
        enemy_id = None
        enemy_count = None
        trait_id = None
        quest_enemies_traits = None
        result: list[QuestEnemiesTraits] = []
        for row in cur.fetchall():
            if quest_id != row[0] or enemy_id != row[1]:
                if quest_enemies_traits is not None:
                    result.append(quest_enemies_traits)
                quest_id = row[0]
                enemy_id = row[1]
                enemy_count = row[2]
                trait_id = row[3]
                quest_enemies_traits = QuestEnemiesTraits(quest_id, enemy_id, enemy_count, [trait_id])
                continue
            trait_id = row[3]
            quest_enemies_traits.traits.append(trait_id)

        if quest_enemies_traits is not None:
            result.append(quest_enemies_traits)
            
        return result