
from doctest import master
from requests_cache import CachedSession
from itertools import groupby
import json
import time
import datetime
import sys
import asyncio

import fgo_api_types.nice as nice
import fgo_api_types.basic as basic
import fgo_api_types.enums as enums

import db

session = None

def init_session(_session: CachedSession = CachedSession(expire_after=600)):
    global session
    if not session:
        session = _session


class TraitSearchQuery:
    trait_id: int | list[int]
    killcount_required: int
    is_or: bool

    def __init__(self, trait_id, killcount_required, is_or):
        self.trait_id = trait_id
        self.killcount_required = killcount_required
        self.is_or = is_or
    
    def __hash__(self):
        if isinstance(self.trait_id, list):
            return hash(",".join(str(self.trait_id)))
        else:
            return hash(self.trait_id)
    
    def __eq__(self, other):
        if isinstance(self.trait_id, list) and isinstance(other.trait_id, list):
            return all(id in other.trait_id for id in self.trait_id) and self.is_or == other.is_or
        else:
            return self.trait_id == other.trait_id and self.is_or == other.is_or

    def __repr__(self) -> str:
        return f'{self.trait_id}|{self.killcount_required}'
    
    @property
    def max_trait_id(self):
        if isinstance(self.trait_id, list):
            return max(self.trait_id)
        else:
            return self.trait_id


class QuestResult:
    id: int
    cost: int
    name: str
    spot_name: str
    war_name: str
    count_foreach_trait: dict[TraitSearchQuery, int]

    def __init__(self, id, ap_cost, name, spot_name, war_name):
        self.id = id
        self.cost = ap_cost
        self.name = name
        self.spot_name = spot_name
        self.war_name = war_name.replace("\n", ", ")
        self.count_foreach_trait = {}

    def to_str(self):
        return f'{self.id}|{self.cost}|{self.name}|{self.spot_name}|{self.war_name}'

    def __repr__(self) -> str:
        return self.to_str()

    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return self.id == other.id


def get_free_quests(region: str = "JP"):
    url = f"https://api.atlasacademy.io/basic/{region}/quest/phase/search?type=free&flag=displayLoopmark&lang=en"
    response = session.get(url)
    free_quests = json.loads(response.text)
    return [basic.BasicQuestPhase.parse_obj(quest) for quest in free_quests]


def get_free_quests_with_trait(trait_query: TraitSearchQuery, region: str = "JP") -> list[basic.BasicQuestPhase] | None:
    if not trait_query or not trait_query.trait_id:
        return None

    if isinstance(trait_query.trait_id, list):
        trait_querystr = "".join([f'&enemyTrait={id}' for id in trait_query.trait_id])
    else:
        trait_querystr = f'&enemyTrait={trait_query.trait_id}'

    url = f"https://api.atlasacademy.io/basic/{region}/quest/phase/search?type=free&flag=displayLoopmark&lang=en{trait_querystr}"
    response = session.get(url)
    free_quests = json.loads(response.text)
    return [basic.BasicQuestPhase.parse_obj(quest) for quest in free_quests]


def get_quest_details(quest_id: int, region: str = "JP"):
    url = f"https://api.atlasacademy.io/nice/{region}/quest/{quest_id}?lang=en"
    response = session.get(url)
    return nice.NiceQuest.parse_obj(json.loads(response.text))


def get_quest_phase_details(quest_id: int, phase: int, region: str = "JP"):
    if region != "JP" and region != "NA":
        region = "JP" # Regions except JP and NA doesn't have enemy data
    url = f"https://api.atlasacademy.io/nice/{region}/quest/{quest_id}/{phase}?lang=en"
    response = session.get(url)
    return nice.NiceQuestPhase.parse_obj(json.loads(response.text))


def get_quest_details_disk(file_name: str, region: str = "JP"):
    with open(file_name, encoding="utf-8") as f:
        all_details = json.load(f)
        return [nice.NiceQuestPhase.parse_obj(detail) for detail in all_details]


def remove_duplicates(list):
    return [i for n, i in enumerate(list) if i not in list[n + 1:]]


async def main():
    init_session()
    region = "JP"
    if len(sys.argv) > 1:
        region = str(sys.argv[1])
    
    if region != "JP" and region != "NA":
        region = "JP"
    
    # copy_data_to_db(region)

    final_results = await get_optimized_quests(region=region, load_from_disk=False)

    total_ap = 0
    for quest, count in final_results.items():
        print(quest)
        for search_query, enemy_count in quest.count_foreach_trait.items():
            if isinstance(search_query.trait_id, list):
                trait_name = ", ".join([enums.TRAIT_NAME[id].value for id in search_query.trait_id])
            else:
                trait_name = enums.TRAIT_NAME[search_query.trait_id].value
            print(f"{trait_name} * {enemy_count} * {count} = {enemy_count * count}")
        print(f'{quest.cost}AP * {count} = {quest.cost * count}AP')
        total_ap += (quest.cost * count)
    print(f"Total: {total_ap}AP")


# Class ID => Trait ID
CLASS_TRAIT_MAP: dict[int, int] = {
    1: 100, # enums.Trait.classSaber
    2: 102, # enums.Trait.classArcher,
    3: 101, # enums.Trait.classLancer,
    4: 103, # enums.Trait.classRider,
    5: 104, # enums.Trait.classCaster,
    6: 105, # enums.Trait.classAssassin,
    7: 106, # enums.Trait.classBerserker,
    8: 107, # enums.Trait.classShielder,
    9: 108, # enums.Trait.classRuler,
    10: 109, # enums.Trait.classAlterEgo,
    11: 110, # enums.Trait.classAvenger,
    25: 117, # enums.Trait.classForeigner,
    28: 120, # enums.Trait.classPretender,
}


async def get_optimized_quests(region: str = "JP", load_from_disk: bool = False) -> dict[QuestResult, int]:
    master_mission_id: int
    target_traits: list[TraitSearchQuery] = []
    import missions
    missions.init_session()
    master_missions = missions.load_missions(region)
    master_missions = [mission for mission in master_missions if mission.startedAt <= int(time.time()) <= mission.endedAt]
    for master_mission in master_missions:
        start = datetime.datetime.fromtimestamp(master_mission.startedAt)
        end = datetime.datetime.fromtimestamp(master_mission.endedAt)
        delta = end - start
        if delta.days == 6: # Weekly
            for mission in master_mission.missions:
                for cond in mission.conds:
                    if cond.detail:
                        if (cond.detail.missionCondType == enums.DetailMissionCondType.DEFEAT_ENEMY_INDIVIDUALITY.value or 
                            cond.detail.missionCondType == enums.DetailMissionCondType.ENEMY_INDIVIDUALITY_KILL_NUM.value):
                            new_target_trait = TraitSearchQuery(cond.detail.targetIds, cond.targetNum, False)
                            existing_target_trait = next((target_trait for target_trait in target_traits if target_trait == new_target_trait), None)
                            if existing_target_trait: 
                                existing_target_trait.killcount_required += (cond.targetNum - existing_target_trait.killcount_required)
                            else:
                                target_traits.append(TraitSearchQuery(cond.detail.targetIds, cond.targetNum, False))
                        elif (cond.detail.missionCondType == enums.DetailMissionCondType.DEFEAT_SERVANT_CLASS.value or 
                            cond.detail.missionCondType == enums.DetailMissionCondType.DEFEAT_ENEMY_CLASS.value):
                            targetids = [CLASS_TRAIT_MAP[targetid] for targetid in cond.detail.targetIds]
                            new_target_trait = TraitSearchQuery(targetids, cond.targetNum, True)
                            existing_target_trait = next((target_trait for target_trait in target_traits if target_trait == new_target_trait), None)
                            if existing_target_trait: 
                                existing_target_trait.killcount_required += (cond.targetNum - existing_target_trait.killcount_required)
                            else:
                                target_traits.append(TraitSearchQuery(targetids, cond.targetNum, True))
            master_mission_id = master_mission.id
            break

    db.init_optimized_quests_db()
    drop_data: list[db.OptimizedQuest] = db.get_optimized_quests(master_mission_id, region)
    if drop_data and len(drop_data) > 0:
        final_results: dict[QuestResult, int] = {}
        for q_id, quest_group in groupby(drop_data, lambda x: x.quest_id):
            count_foreach_target: dict[TraitSearchQuery, int] = {}
            quest_details = get_quest_details(q_id, region)
            for optimized_quest in quest_group:
                if "," in optimized_quest.target_id:
                    target_id = [int(id) for id in optimized_quest.target_id.split(",")]
                else:
                    target_id = int(optimized_quest.target_id)

                search_query = TraitSearchQuery(target_id, 0, optimized_quest.is_or)
                count_foreach_target[search_query] = optimized_quest.target_count
            quest_result = QuestResult(
                q_id,
                quest_details.consume,
                quest_details.name,
                quest_details.spotName,
                quest_details.warLongName.replace("\n", ", "),
            )
            quest_result.count_foreach_trait = count_foreach_target
            final_results[quest_result] = optimized_quest.count
        return final_results

    quests = get_free_quests(region)

    # Gets max phase (repeatable quest)
    quests_max_phase = [
        max(quest_group, key=lambda x: x.phase)
        for key, quest_group in groupby(quests, lambda x: x.id)
    ]

    quests_max_phase = [quest for quest in quests_max_phase if quest.afterClear == nice.NiceQuestAfterClearType.repeatLast]

    quests = None

    if load_from_disk:
        copy_data_to_db()

    # json_text = []
    # for quest in nice_questphases[0:10]:
    #     json_text.append(quest.json())
    # with open("test_lite.json", "w", encoding="utf-8") as outfile:
    #     outfile.write(f'[{",".join(json_text)}]')

    # target_traits: list[TraitSearchQuery] = [
    #     TraitSearchQuery(201, 15),
    #     TraitSearchQuery(2019, 15),
    #     TraitSearchQuery([200, 1000], 3),
    #     TraitSearchQuery([301, 1000], 3),
    #     TraitSearchQuery([303, 1000], 3),
    # ]

    quest_results: list[QuestResult] = []
    for quest_basic in quests_max_phase:
        await asyncio.to_thread(create_quest_result, quest_basic, target_traits, quest_results)

    import cvxpy
    import numpy as np

    # quest_results contains the activities data (cost, number of enemies for each traits)
    number_of_times = cvxpy.Variable(len(quest_results), integer=True)
    energy_costs = np.array([quest_result.cost for quest_result in quest_results])
    total_costs = energy_costs @ number_of_times
    constraints = [number_of_times >= 0] # Number of times cannot be negative
    
    for target_trait in target_traits: # target_traits is kill requirements for each trait
        enemy_count_foreach_trait = []
        for quest_result in quest_results:
            has_target_trait = False
            for trait, enemy_count in quest_result.count_foreach_trait.items():
                # count_foreach_trait is a dictionary containing [trait - enemy count for that trait] for a activity
                if target_trait == trait:
                    enemy_count_foreach_trait.append(enemy_count)
                    has_target_trait = True
                    break
            if not has_target_trait:
                enemy_count_foreach_trait.append(0)
        # Add kill count requirements to constraints
        constraints.append(enemy_count_foreach_trait @ number_of_times >= target_trait.killcount_required)
    
    prob = cvxpy.Problem(cvxpy.Minimize(total_costs), constraints)
    prob.solve(solver=cvxpy.GLPK_MI)

    final_results: dict[QuestResult, int] = {
        quest_results[idx]: int(value)
        for idx, value in enumerate(number_of_times.value)
        if not value == 0
    }

    # Insert DB
    optimized_quests: list[db.OptimizedQuest] = []
    for result, count in final_results.items():
        for search_query, enemy_count in result.count_foreach_trait.items():
            optimized_quest: db.OptimizedQuest = db.OptimizedQuest(None, None, None, None, None, False)
            optimized_quest.master_mission_id = master_mission_id
            optimized_quest.quest_id = result.id
            if isinstance(search_query.trait_id, list):
                optimized_quest.target_id = ",".join([str(id) for id in search_query.trait_id])
            else:
                optimized_quest.target_id = search_query.trait_id
            optimized_quest.target_count = enemy_count
            optimized_quest.count = count
            optimized_quest.is_or = search_query.is_or
            optimized_quests.append(optimized_quest)
    if len(optimized_quests) > 0:
        db.insert_optimized_quests(optimized_quests, region)

    return final_results


def create_quest_result(
    quest: basic.BasicQuestPhase,
    target_traits: list[TraitSearchQuery],
    quest_results: list[QuestResult],
):
    quest_enemies = db.get_quest_enemies(quest.id)
    if quest_enemies is None or len(quest_enemies) == 0:
        return
    quest_result = QuestResult(quest.id, quest.consume, quest.name, quest.spotName, quest.warLongName)
    matched = False
    for enemy in quest_enemies:
        for target in target_traits:
            enemy_count = 0
            target_trait_id = target.trait_id
            if isinstance(target_trait_id, list):
                if target.is_or:
                    if any(target_id in [trait_id for trait_id in enemy.traits] for target_id in target_trait_id):
                        enemy_count += enemy.count
                else:
                    if all(target_id in [trait_id for trait_id in enemy.traits] for target_id in target_trait_id):
                        enemy_count += enemy.count
            else:
                if target_trait_id in [trait_id for trait_id in enemy.traits]:
                    enemy_count += enemy.count
            if enemy_count == 0:
                continue
            quest_result.count_foreach_trait[target] = quest_result.count_foreach_trait.get(target, 0) + enemy_count
                
            matched = True
    if not matched:
        return
    quest_results.append(quest_result)


def init_data_from_api():
    init_session()
    region = "JP"
    quests = get_free_quests(region)

    # Gets max phase (repeatable quest)
    quests_max_phase = [
        max(quest_group, key=lambda x: x.phase)
        for key, quest_group in groupby(quests, lambda x: x.id)
    ]
    
    quests_with_details = [get_quest_phase_details(quest.id, quest.phase, region) for quest in quests_max_phase if quest.afterClear == nice.NiceQuestAfterClearType.repeatLast]
    json_text = []
    for quest in quests_with_details:
        json_text.append(quest.json())
    with open("data.json", "w", encoding="utf-8") as outfile:
        outfile.write(f'[{",".join(json_text)}]')


def copy_data_to_db(region: str = "JP"):
    nice_questphases = get_quest_details_disk("test.json", region)
    for quest in nice_questphases:
        all_enemies = [enemy for stage in quest.stages for enemy in stage.enemies]
        db.insert_quest_enemies(quest.id, all_enemies)


if __name__ == "__main__":
    asyncio.run(main())
