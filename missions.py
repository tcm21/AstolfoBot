
from requests_cache import CachedSession
import json
import time
import datetime
import fgo_api_types.nice as nice
import fgo_api_types.basic as basic
import fgo_api_types.enums as enums

from text_builders import title_case

session = None

def init_session(_session: CachedSession = CachedSession(expire_after=600)):
    global session
    if not session:
        session = _session


def load_missions(region: str = "JP") -> list[nice.NiceMasterMission]:
    url = f"https://api.atlasacademy.io/export/{region}/nice_master_mission.json"
    response = session.get(url)
    missions = json.loads(response.text)
    result = []
    for mission in missions:
        nice_mission = nice.NiceMasterMission.parse_obj(mission)
        result.append(nice_mission)
    return result


def get_items(region: str = "JP") -> list[nice.NiceItem]:
    if region == "JP":
        url = f"https://api.atlasacademy.io/export/JP/nice_item_lang_en.json"
    else:
        url = f"https://api.atlasacademy.io/export/NA/nice_item.json"
    response = session.get(url)
    items = json.loads(response.text)
    result = []
    for item in items:
        nice_item = nice.NiceItem.parse_obj(item)
        result.append(nice_item)
    return result


def get_servants(region: str = "JP") -> list[basic.BasicServant]:
    if region == "JP":
        url = f"https://api.atlasacademy.io/export/JP/basic_servant_lang_en.json"
    else:
        url = f"https://api.atlasacademy.io/export/NA/basic_servant.json"
    response = session.get(url)
    servants = json.loads(response.text)
    result = []
    for servant in servants:
        nice_svt = basic.BasicServant.parse_obj(servant)
        result.append(nice_svt)
    return result


def get_current_weeklies(region: str = "JP"):
    result = []
    master_missions = load_missions(region)
    master_missions = [mission for mission in master_missions if mission.startedAt <= int(time.time()) <= mission.endedAt]
    for master_mission in master_missions:
        start = datetime.datetime.fromtimestamp(master_mission.startedAt)
        end = datetime.datetime.fromtimestamp(master_mission.endedAt)
        delta = end - start
        if delta.days == 6: # Weekly
            for idx, mission in enumerate(master_mission.missions):
                desc = describe_missions(mission, region)
                if idx > 0: 
                    result.append('')
                result.append(f'**Mission {idx + 1}:**')
                result.extend(desc)
            break

    return result


def describe_missions(mission: nice.NiceEventMission, region: str = "JP"):
    desc = []
    desc.append(mission.detail)
    for cond in mission.conds:
        if cond.missionProgressType != nice.NiceMissionProgressType.clear:
            continue
        if cond.detail:
            match cond.detail.missionCondType:
                case (enums.DetailMissionCondType.QUEST_CLEAR_NUM_1.value |
                      enums.DetailMissionCondType.QUEST_CLEAR_NUM_2.value |
                      enums.DetailMissionCondType.QUEST_CLEAR_NUM_INCLUDING_GRAILFRONT.value
                    ):
                    desc.append(f"Clear any quest {cond.targetNum} times")
                case enums.DetailMissionCondType.MAIN_QUEST_DONE.value:
                    desc.append(f"Clear any main quest in Arc 1 and Arc 2 {cond.targetNum} times")
                case enums.DetailMissionCondType.ENEMY_KILL_NUM.value:
                    desc.append(f"Defeat {cond.targetNum} enemies")
                case enums.DetailMissionCondType.DEFEAT_ENEMY_INDIVIDUALITY.value | enums.DetailMissionCondType.ENEMY_INDIVIDUALITY_KILL_NUM.value:
                    traits = []
                    for target_id in cond.detail.targetIds:
                        trait = enums.TRAIT_NAME[target_id]
                        traits.append(f'[{title_case(trait.value)}](https://apps.atlasacademy.io/db/{region}/entities?trait={target_id})')
                    desc.append(f"Defeat {cond.targetNum} enemies with traits [{', '.join(traits)}]")                    # desc.append(f'[List of free quests](https://apps.atlasacademy.io/db/{region}/quests?type=free&flag=displayLoopmark{"".join(trait_ids_querystr)}) that has [{", ".join(traits)}]')
                    
                case enums.DetailMissionCondType.DEFEAT_SERVANT_CLASS.value | enums.DetailMissionCondType.DEFEAT_ENEMY_CLASS.value:
                    classes = []
                    for target_id in cond.detail.targetIds:
                        svt_class = enums.CLASS_NAME[target_id]
                        classes.append(title_case(svt_class.value))
                    desc.append(f"Defeat {cond.targetNum} enemies with class [{', '.join(classes)}]")
                case enums.DetailMissionCondType.DEFEAT_ENEMY_NOT_SERVANT_CLASS.value:
                    classes = []
                    for target_id in cond.detail.targetIds:
                        svt_class = enums.CLASS_NAME[target_id]
                        classes.append(title_case(svt_class.value))
                    desc.append(f"Defeat {cond.targetNum} enemies with class [{', '.join(classes)}] except servants")
                case enums.DetailMissionCondType.BATTLE_SVT_CLASS_IN_DECK.value:
                    classes = []
                    for target_id in cond.detail.targetIds:
                        svt_class = enums.CLASS_NAME[target_id]
                        classes.append(title_case(svt_class.value))
                    desc.append(f"Complete any quest {cond.targetNum} times with class [{', '.join(classes)}] in party")
                case enums.DetailMissionCondType.ITEM_GET_BATTLE.value | enums.DetailMissionCondType.ITEM_GET_TOTAL.value:
                    items = get_items(region)
                    target_items = []
                    for target_id in cond.detail.targetIds[0:5]:
                        target_items.append(next(f'[{item.name}](https://apps.atlasacademy.io/db/{region}/item/{item.id})' for item in items if item.id == target_id))
                    desc.append(f"Obtain [{', '.join(target_items)}{', ...' if len(cond.detail.targetIds) > 5 else ''}] x {cond.targetNum}")
                case enums.DetailMissionCondType.BATTLE_SVT_INDIVIDUALITY_IN_DECK.value:
                    traits = []
                    for target_id in cond.detail.targetIds:
                        trait = enums.TRAIT_NAME[target_id]
                        traits.append(f'[{title_case(trait.value)}](https://apps.atlasacademy.io/db/{region}/entities?trait={target_id})')
                    desc.append(f"Complete any quest {cond.targetNum} times with traits [{', '.join(traits)}] in party")
                case enums.DetailMissionCondType.BATTLE_SVT_ID_IN_DECK_1.value | enums.DetailMissionCondType.BATTLE_SVT_ID_IN_DECK_2.value:
                    servants = get_servants(region)
                    target_servants = []
                    for target_id in cond.detail.targetIds:
                        target_servants.append(next(f'[{svt.name}](https://apps.atlasacademy.io/db/{region}/servant/{svt.id})' for svt in servants if svt.id == target_id))
                    desc.append(f"Complete any quest {cond.targetNum} times with [{', '.join(target_servants)}] in party")
                case enums.DetailMissionCondType.SVT_GET_BATTLE.value:
                    desc.append(f"Obtain {cond.targetNum} embers")
                case enums.DetailMissionCondType.FRIEND_POINT_SUMMON.value:
                    desc.append(f"Friend summon {cond.targetNum} times")
                case _:
                    desc.append(f'mission detail type {cond.missionCondType} num {cond.targetNum} targets {", ".join(cond.detail.targetIds)}')

    if mission.gifts:
        gifts = []
        for gift in mission.gifts:
            match gift.type:
                case nice.NiceGiftType.servant.value | nice.NiceGiftType.eventSvtJoin.value | nice.NiceGiftType.eventSvtGet.value:
                    servants = get_servants(region)
                    gifts.append(next(f'[[{svt.name}](https://apps.atlasacademy.io/db/{region}/servant/{svt.id})] x {gift.num}' for svt in servants if svt.id == gift.objectId))
                case nice.NiceGiftType.item.value:
                    items = get_items(region)
                    gifts.append(next(f'[[{item.name}](https://apps.atlasacademy.io/db/{region}/item/{item.id})] x {gift.num}' for item in items if item.id == gift.objectId))
                # case nice.NiceGiftType.equip.value:
                #     # TODO: mystic code
                #     pass
                # case nice.NiceGiftType.questRewardIcon.value:
                #     pass
                # case nice.NiceGiftType.costumeGet.value | nice.NiceGiftType.costumeRelease.value:
                #     # TODO: Costume
                #     pass
                # case nice.NiceGiftType.commandCode.value:
                #     # TODO: Command codes
                #     pass
                # case nice.NiceGiftType.eventPointBuff.value:
                #     # TODO: Command codes
                #     pass
                case _:
                    gifts.append(f'{gift.type} {gift.objectId} {gift.priority} {gift.num}')

        desc.append(f'Rewards: {", ".join(gifts)}')
            
    return desc
