import requests_cache
import json

SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def get_skill_description(session: requests_cache.CachedSession, skill, sub_skill: bool = False):
    skill_descs = []
    if not sub_skill: skill_descs.append(f'**Base Cooldown: ** {skill.get("coolDown")[0]}')
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

        buff_type = function.get("buffs")[0].get("type") if function.get("buffs") and len(function.get("buffs")) > 0 else ""
        func_type = function.get("funcType")
        if sval_value:
            valuesTextList = []
            if buff_type.endswith("Function"):
                func_skill = get_skill_by_id(session, sval_value)
                func_skill_desc = get_skill_description(session=session, skill=func_skill, sub_skill=True)
                values_text += func_skill_desc
                # func_skill_tvals = function.get("buffs")[0].get("tvals")
                # for sub_func in func_skill.get("functions"):
                #     for svalIdx, sval in enumerate(sub_func.get("svals")):
                #         if not sval.get("Value"): continue
                #         valuesTextList.append(f'{get_sval_from_buff(sval.get("Value"), "", sub_func.get("funcType"))}{str(svalIdx + 1).translate(SUB)}')
                #     values_text = f'{sub_func.get("funcPopupText")}\n'
                #     values_text += f'Values: {" - ".join(valuesTextList)}' if len(valuesTextList) > 0 else ""
            elif all(sval.get("Value") == svals[0].get("Value") for sval in svals):
                # All values are the same
                values_text = f'Value: {get_sval_from_buff(svals[0].get("Value"), buff_type, func_type)}'
            else:
                for svalIdx, sval in enumerate(svals):
                    valuesTextList.append(f'{get_sval_from_buff(sval.get("Value"), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
                values_text = f'Value: {" - ".join(valuesTextList)}'

        if sval_rate and sval_rate != 1000 and sval_rate != 5000:
            chances_list = []
            if all(sval.get("Rate") == svals[0].get("Rate") for sval in svals):
                chances_text = f'Chance: {get_sval_from_buff(svals[0].get("Rate"), buff_type, func_type)}'
            else:
                for svalIdx, sval in enumerate(svals):
                    chances_list.append(f'{get_sval_from_buff(sval.get("Rate"), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
                chances_text = f'Chance: {" - ".join(chances_list)}'

        if sval_userate and sval_userate != 1000 and sval_userate != 5000:
            usechances_list = []
            if all(sval.get("UseRate") == svals[0].get("UseRate") for sval in svals):
                usechance_text = f'Chance: {svals[0].get("UseRate") / 10}%'
            else:
                for svalIdx, sval in enumerate(svals):
                    usechances_list.append(f'{sval.get("UseRate") / 10}%{str(svalIdx + 1).translate(SUB)}')
                usechance_text = f'Chance: {" - ".join(usechances_list)}'

        if sval_count and sval_count > 0:
            count_text = f'{sval_count} Times'
        if sval_turns and sval_turns > 0:
            turns_text = f'{sval_turns} Turns'

        turns_count_text = ", ".join([count_text, turns_text]).strip(", ")
        if turns_count_text: turns_count_text = f"({turns_count_text})"
            
        if not sub_skill:
            skill_descs.append(f'**Effect {funcIdx + 1}**: {function.get("funcPopupText")} {turns_count_text}')
        else:
            skill_descs.append(f'**↳Triggered Effect {funcIdx + 1}**: {function.get("funcPopupText")} {turns_count_text}')

        if chances_text: skill_descs.append(f'{chances_text}')
        if usechance_text: skill_descs.append(f'{usechance_text}')
        if values_text: skill_descs.append(f'{values_text}')
    return "\n".join(skill_descs)


def get_sval_from_buff(value: int, buff_type: str, func_type: str) -> str:
    if not buff_type:
        if func_type == ("gainNp") or func_type == ("damageNp"):
            return f'{str(value / 100).rstrip("0").rstrip(".")}%'
    if buff_type.startswith("up") or buff_type.startswith("down"):
        return f'{str(value / 10).rstrip("0").rstrip(".")}%'
    if buff_type.startswith("regainNp"):
        return str(value / 100).rstrip("0").rstrip(".")
    if buff_type.startswith("donotAct"):
        return f'{str(value / 10).rstrip("0").rstrip(".")}%'
    return str(value).rstrip("0").rstrip(".")


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