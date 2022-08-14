import requests_cache
import json
import re
from enum import Enum

SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

class NpFunctionType(Enum):
    LEVEL = 1
    OVERCHARGE = 2
    NONE = 3

def get_np_function_type(function) -> NpFunctionType:
    svals = function.get("svals")
    if svals[0].get("Value") != svals[1].get("Value"):
        return NpFunctionType.LEVEL
    
    svals2 = function.get("svals2")
    if svals[0].get("Value") != svals2[1].get("Value"):
        return NpFunctionType.OVERCHARGE
    
    return NpFunctionType.NONE


def get_skill_description(session: requests_cache.CachedSession, skill, sub_skill: bool = False):
    skill_descs = []
    if not sub_skill and skill.get("coolDown"): skill_descs.append(f'**Base Cooldown: ** {skill.get("coolDown")[0]}')
    is_np = False
    if skill.get("card"): is_np = True # Noble phantasms
    for funcIdx, function in enumerate(skill.get("functions")):
        svals = function.get("svals")
        sval_rate = svals[0].get("Rate")
        sval_turns = svals[0].get("Turn")
        sval_count = svals[0].get("Count")
        sval_value = svals[0].get("Value")
        sval_userate = svals[0].get("UseRate")

        chances_text = ""
        values_text = ""
        turns_text = ""
        count_text = ""
        usechance_text = ""

        np_function_type = NpFunctionType.NONE
        if is_np: np_function_type = get_np_function_type(function)

        buff_type = function.get("buffs")[0].get("type") if function.get("buffs") and len(function.get("buffs")) > 0 else ""
        func_type = function.get("funcType")
        if sval_value:
            valuesTextList = []
            if buff_type.endswith("Function"):
                func_skill = get_skill_by_id(session, sval_value)
                func_skill_desc = get_skill_description(session=session, skill=func_skill, sub_skill=True)
                values_text += func_skill_desc
            elif all(sval.get("Value") == svals[0].get("Value") for sval in svals):
                # All values are the same
                if is_np and np_function_type == NpFunctionType.OVERCHARGE:
                    values_text = get_overcharge_values(function, buff_type, func_type)
                else:
                    values_text = f'Value: {get_sval_from_buff(svals[0].get("Value"), buff_type, func_type)}'
            else:
                for svalIdx, sval in enumerate(svals):
                    valuesTextList.append(f'{get_sval_from_buff(sval.get("Value"), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
                np_text = " (Level)" if is_np and np_function_type == NpFunctionType.LEVEL else ""
                values_text = f'Value{np_text}: {" · ".join(valuesTextList)}'

        if sval_rate and sval_rate != 1000 and sval_rate != 5000:
            chances_list = []
            if all(sval.get("Rate") == svals[0].get("Rate") for sval in svals):
                chances_text = f'Chance: {remove_zeros_decimal(svals[0].get("Rate") / 10)}%'
            else:
                for svalIdx, sval in enumerate(svals):
                    chances_list.append(f'{remove_zeros_decimal(sval.get("Rate") / 10)}{str(svalIdx + 1).translate(SUB)}')
                chances_text = f'Chance: {" · ".join(chances_list)}'

        if sval_userate and sval_userate != 1000 and sval_userate != 5000:
            usechances_list = []
            if all(sval.get("UseRate") == svals[0].get("UseRate") for sval in svals):
                usechance_text = f'Chance: {remove_zeros_decimal(svals[0].get("UseRate") / 10)}%'
            else:
                for svalIdx, sval in enumerate(svals):
                    usechances_list.append(f'{remove_zeros_decimal(sval.get("UseRate") / 10)}%{str(svalIdx + 1).translate(SUB)}')
                usechance_text = f'Chance: {" · ".join(usechances_list)}'

        if sval_count and sval_count > 0:
            count_text = f'{sval_count} Times'
        if sval_turns and sval_turns > 0:
            turns_text = f'{sval_turns} Turns'

        turns_count_text = ", ".join([count_text, turns_text]).strip(", ")
        if turns_count_text: turns_count_text = f"({turns_count_text})"
            
        if func_type == "damageNp":
            skill_descs.append(f'**Effect {funcIdx + 1}**: Deals damage to [{title_case(function.get("funcTargetType"))}]')
        elif not sub_skill:
            skill_descs.append(f'**Effect {funcIdx + 1}**: {function.get("funcPopupText")} to [{title_case(function.get("funcTargetType"))}] {turns_count_text}')
        else:
            skill_descs.append(f'**↳Triggered Effect {funcIdx + 1}**: {function.get("funcPopupText")} to [{title_case(function.get("funcTargetType"))}] {turns_count_text}')

        if chances_text: skill_descs.append(f'{chances_text}')
        if usechance_text: skill_descs.append(f'{usechance_text}')
        if values_text: skill_descs.append(f'{values_text}')
    return "\n".join(skill_descs)


def get_overcharge_values(function, buff_type, func_type):
    valuesTextList = []
    for svalIdx, sval in enumerate([
        function.get("svals")[0],
        function.get("svals2")[0],
        function.get("svals3")[0],
        function.get("svals4")[0],
        function.get("svals5")[0],
    ]):
        valuesTextList.append(f'{get_sval_from_buff(sval.get("Value"), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
    values_text = f'Value (Overcharge): {" - ".join(valuesTextList)}'
    return values_text


def get_sval_from_buff(value: int, buff_type: str, func_type: str) -> str:
    if not buff_type:
        if func_type == ("gainNp"):
            return f'{remove_zeros_decimal(value / 100)}%'
        elif func_type == ("damageNp"):
            return f'{remove_zeros_decimal(value / 10)}%'
    if buff_type.startswith("up") or buff_type.startswith("down"):
        return f'{remove_zeros_decimal(value / 10)}%'
    if buff_type.startswith("regainNp"):
        return remove_zeros_decimal(value / 100)
    if buff_type.startswith("donotAct"):
        return f'{remove_zeros_decimal(value / 10)}%'
    return remove_zeros_decimal(value)


def remove_zeros_decimal(value):
    return str(value).rstrip("0").rstrip(".") if "." in str(value) else str(value)


def title_case(string):
    if not string:
        return
    words = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', string)).split()
    if len(words) > 0:
        words[0] = words[0][0].upper() + words[0][1:]
    return " ".join(words)


def get_skill_by_id(session: requests_cache.CachedSession, id: int, region: str = "JP"):
    """Get skill by ID

    Args:
        id (int): Skill ID
        region (str, optional): Region. Defaults to "JP".

    Returns:
        Skill object
    """
    response = session.get(
        f"https://api.atlasacademy.io/nice/{region}/skill/{id}")
    skill = json.loads(response.text)
    if skill.get('detail') == "Skill not found":
        return None
    else:
        return skill
