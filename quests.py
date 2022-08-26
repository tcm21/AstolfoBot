
from requests_cache import CachedSession
from itertools import groupby
import json
import time
import datetime
import sys

import fgo_api_types.nice as nice
import fgo_api_types.basic as basic
import fgo_api_types.enums as enums

session = None

def init_session(_session: CachedSession = CachedSession(expire_after=600)):
    global session
    if not session:
        session = _session


class TraitSearchQuery:
    trait_id: int | list[int]
    remain: int

    def __init__(self, trait_id, remain):
        self.trait_id = trait_id
        self.remain = remain
    
    def __hash__(self):
        if isinstance(self.trait_id, list):
            return hash(",".join(str(self.trait_id)))
        else:
            return hash(self.trait_id)
    
    def __eq__(self, other):
        if isinstance(self.trait_id, list) and isinstance(other.trait_id, list):
            return all(id in other.trait_id for id in self.trait_id)
        else:
            return self.trait_id == other.trait_id
    
    def __repr__(self) -> str:
        return f'{self.trait_id}|{self.remain}'


class QuestEnemies:
    id: int
    ap_cost: int
    enemies: list[nice.QuestEnemy]
    name: str
    spot_name: str
    war_name: str

    def __init__(self, id, ap_cost, enemies, name, spot_name, war_name):
        self.id = id
        self.ap_cost = ap_cost
        self.enemies = enemies
        self.name = name
        self.spot_name = spot_name
        self.war_name = war_name.replace("\n", ", ")


class QuestResult:
    id: int
    ap_cost: int
    name: str
    spot_name: str
    war_name: str
    count_foreach_target: dict[TraitSearchQuery, int]

    def __init__(self, id, ap_cost, name, spot_name, war_name):
        self.id = id
        self.ap_cost = ap_cost
        self.name = name
        self.spot_name = spot_name
        self.war_name = war_name
        self.count_foreach_target = {}

    def to_str(self):
        return f'{self.id}|{self.ap_cost}|{self.name}|{self.spot_name}|{self.war_name}'

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


def get_quest_details(quest_id: int, phase: int, region: str = "JP"):
    url = f"https://api.atlasacademy.io/nice/{region}/quest/{quest_id}/{phase}?lang=en"
    response = session.get(url)
    return nice.NiceQuestPhase.parse_obj(json.loads(response.text))


def get_quest_details_disk(region: str = "JP"):
    with open("test.json", encoding="utf-8") as f:
        all_details = json.load(f)
        return [nice.NiceQuestPhase.parse_obj(detail) for detail in all_details]


def remove_duplicates(list):
    return [i for n, i in enumerate(list) if i not in list[n + 1:]]


def main():
    init_session()
    region = "JP"
    if len(sys.argv) > 0:
        region = str(sys.argv[0])
    
    if region != "JP" and region != "NA":
        region = "JP"

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
                    if (cond.detail and
                        (cond.detail.missionCondType == enums.DetailMissionCondType.DEFEAT_ENEMY_INDIVIDUALITY.value or 
                        cond.detail.missionCondType == enums.DetailMissionCondType.ENEMY_INDIVIDUALITY_KILL_NUM.value)
                    ):
                        target_traits.append(TraitSearchQuery(cond.detail.targetIds, cond.targetNum))

    # quests = [get_free_quests(region)]
    quests: list[basic.BasicQuestPhase] = []
    for target_trait in target_traits:
        quests_with_traits = get_free_quests_with_trait(target_trait, region)
        quests.extend(quests_with_traits)
    
    quests = remove_duplicates(quests)

    # Gets max phase (repeatable quest)
    quests_max_phase = [
        max(quest_group, key=lambda x: x.phase)
        for key, quest_group in groupby(quests, lambda x: x.id)
    ]

    quests_max_phase = [quest for quest in quests_max_phase if quest.afterClear == nice.NiceQuestAfterClearType.repeatLast]

    quests = None

    # Loads from disk
    # all_details = get_quest_details_disk(region)
    # quests_with_details = [next(detail for detail in all_details if detail.id == quest.id) for quest in quests_max_phase if quest.afterClear == nice.NiceQuestAfterClearType.repeatLast]
    # all_details = None

    # Loads from API
    # quests_with_details = [get_quest_details(quest.id, quest.phase, region) for quest in quests_max_phase]

    # target_traits: list[TraitSearchQuery] = [
    #     TraitSearchQuery(201, 15),
    #     TraitSearchQuery(2019, 15),
    #     TraitSearchQuery([200, 1000], 3),
    #     TraitSearchQuery([301, 1000], 3),
    #     TraitSearchQuery([303, 1000], 3),
    # ]

    qes: list[QuestEnemies] = []
    for quest_basic in quests_max_phase:
        quest = get_quest_details(quest_basic.id, quest_basic.phase, region)
        all_enemies = [enemy for stage in quest.stages for enemy in stage.enemies]
        qe = QuestEnemies(quest.id, quest.consume, all_enemies, quest.name, quest.spotName, quest.warLongName)
        qes.append(qe)
    quests_with_details = None

    quest_results: list[QuestResult] = []
    for q in qes:
        quest_result = QuestResult(q.id, q.ap_cost, q.name, q.spot_name, q.war_name)
        matched = False
        for enemy in q.enemies:
            for target in target_traits:
                enemy_count = 0
                target_trait_id = target.trait_id
                if isinstance(target_trait_id, list):
                    if all(target_id in [enemy_trait.id for enemy_trait in enemy.traits] for target_id in target_trait_id):
                        enemy_count += 1
                else:
                    if target_trait_id in [enemy_trait.id for enemy_trait in enemy.traits]:
                        enemy_count += 1
                if enemy_count == 0:
                    continue
                quest_result.count_foreach_target[target] = quest_result.count_foreach_target.get(target, 0) + enemy_count
                matched = True
        if not matched:
            continue
        quest_results.append(quest_result)

    qes = None

    final_results: dict[QuestResult, int] = {}
    while (any(target.remain > 0 for target in target_traits)):
        quest_results.sort(key=lambda r: get_score(r))
        get_final_results(target_traits, quest_results, final_results)
    
    quest_results = None

    total_ap = 0
    for quest, count in final_results.items():
        print(quest)
        for search_query, enemy_count in quest.count_foreach_target.items():
            if isinstance(search_query.trait_id, list):
                trait_name = ", ".join([enums.TRAIT_NAME[id].value for id in search_query.trait_id])
            else:
                trait_name = enums.TRAIT_NAME[search_query.trait_id].value
            print(f"{trait_name} * {enemy_count}")
        print(f'{quest.ap_cost}AP * {count} = {quest.ap_cost * count}AP')
        total_ap += (quest.ap_cost * count)
    print(f"Total: {total_ap}AP")


def get_final_results(target_traits: list[TraitSearchQuery], quest_results: list[QuestResult], final_results: dict[QuestResult, int]):
    for quest_result in quest_results:
        quest_count = 0
        remove_targets: set[TraitSearchQuery] = set()
        while len(target_traits) > 0 and (all(target.remain > 0 for target in target_traits)):
            for search_query, enemy_count in quest_result.count_foreach_target.items():
                if not search_query in target_traits:
                    continue
                search_query.remain -= enemy_count
                if search_query.remain <= 0:
                    remove_targets.add(search_query)
            quest_count += 1
        for remove_target in remove_targets:
            target_traits.remove(remove_target)

        if quest_count > 0:
            final_results[quest_result] = quest_count

        if len(remove_targets) > 0:
            return


def get_score(r: QuestResult) -> float:
    sum = 0
    for query, count in r.count_foreach_target.items():
        if query.remain <= 0:
            continue
        sum += count

    return -(sum / r.ap_cost) 


if __name__ == "__main__":
    main()


def init_data_from_api():
    init_session()
    region = "JP"
    quests = get_free_quests(region)

    # Gets max phase (repeatable quest)
    quests_max_phase = [
        max(quest_group, key=lambda x: x.phase)
        for key, quest_group in groupby(quests, lambda x: x.id)
    ]
    
    quests_with_details = [get_quest_details(quest.id, quest.phase, region) for quest in quests_max_phase if quest.afterClear == nice.NiceQuestAfterClearType.repeatLast]
    json_text = []
    for quest in quests_with_details:
        json_text.append(quest.json())
    with open("data.json", "w", encoding="utf-8") as outfile:
        outfile.write(f'[{",".join(json_text)}]')
    