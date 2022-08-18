import requests_cache
import json
from itertools import groupby

from text_builders import get_skill_by_id, get_servant_by_id

session = None

def init_session(_session: requests_cache.CachedSession = None):
    global session
    if not _session:
        session = requests_cache.CachedSession(expire_after=600)
    elif not session:
        session = _session


def get_skills_with_type(type: str, flag: str = "skill", target: str = "", region: str = "JP"):
    """Get a list of skills or NP with the selected effects.

    Args:
        type (str): Effect name,
        flag (str, optional): "skill" or "NP". Defaults to "skill".
        target (str): Effect target
        region (str): Region (Default: JP)

    Returns:
        A list of skill objects with the specified effect.
    """
    if not type:
        return None
    functions = get_functions(type=type, target=target, region=region)
    found_skills = get_skills_from_functions(functions, flag, target, region)
    if flag == "NP":
        # One extra step for finding skills nested inside NPs (e.g. Miyu)
        found_skills.extend(get_skills_from_functions(functions, "skill", target, region, "NP"))
    return found_skills


def get_skills_with_trait(trait: str, flag: str = "skill", target: str = "", region: str = "JP"):
    """Get a list of skills or NP that are effective against the specified trait.

    Args:
        trait (str): Trait ID
        flag (str, optional): "skill" or "NP". Defaults to "skill".
        target (str): Effect target
        region (str): Region (Default: JP)

    Returns:
        A list of skill objects with the specified effect.
    """
    if not trait:
        return None

    # Search by buffs
    skills_by_buff = get_skills_with_buff(flag=flag, target=target, trait=trait, region=region)

    result = None

    # Search by functions
    if flag == "skill":
        functions = get_functions(target=target, trait=trait, region=region)
        found_skills = get_skills_from_functions(functions, flag, target, region)
        found_skills.extend(skills_by_buff)
        result = found_skills
    elif flag == "NP":
        found_nps = get_nps_with_trait(trait, region)
        found_nps.extend(skills_by_buff)
        result = found_nps

    return result


def get_skills_with_buff(buff_type: str = "", flag: str = "skill", target: str = "", trait: str = "", region: str = "JP"):
    if not buff_type and not trait:
        return None
    buff_query = ""
    if buff_type:
        buff_query = f"&type={buff_type}"
    trait_query = ""
    if trait:
        trait_query = f"&tvals={trait}"
    url = f"https://api.atlasacademy.io/basic/{region}/buff/search?reverse=true&reverseDepth=servant&reverseData=basic&lang=en&{buff_query}{trait_query}"
    response = session.get(url)
    buffs = json.loads(response.text)
    skills = []
    for buff in buffs:
        functions = buff.get("reverse").get("basic").get("function")
        if flag == "skill":
            skills.extend(get_skills_from_functions(functions, "skill", target, region))
        elif flag == "NP":
            skills.extend(get_skills_from_functions(functions, "NP", target, region))
            skills.extend(get_skills_from_functions(functions, "skill", target, region, "NP"))

    return skills


def get_functions(type: str = "", target: str = "", trait: str = "", region: str = "JP"):
    """Gets all the effects (functions) with the specified effect.

    Args:
        type (str): Effect name
        target (str): Effect target
        region (str): Region (Default: JP)

    Returns:
        A list of functions with the specified effect.
    """
    functions = []
    
    if not type and not target and not trait:
        return []
    type_query = ""
    if type:
        type_query = f"&type={type}"
    target_query = ""
    if target:
        target_query = f"&targetType={target}"
    trait_query = ""
    trait_query2 = ""
    if trait:
        trait_query = f"&tvals={trait}"
        trait_query2 = f"&vals={trait}"
    url = f"https://api.atlasacademy.io/basic/{region}/function/search?reverse=true&lang=en&reverseDepth=servant{type_query}{target_query}{trait_query}"
    response = session.get(url)
    functions = json.loads(response.text)

    if trait:
        # tvals and vals are both traits
        url = f"https://api.atlasacademy.io/basic/{region}/function/search?reverse=true&lang=en&reverseDepth=servant{type_query}{target_query}{trait_query2}"
        response = session.get(url)
        functions.extend(json.loads(response.text))

    return functions



def get_skills_from_functions(functions, flag: str = "skill", target: str = "", region: str = "JP", flag2: str = ""):
    if not flag2: flag2 = flag # For searching skills triggered by NP
    found_skills = []
    for function in functions:
        if target and function.get("funcTargetType") != target:
            continue
        for skill in function.get('reverse').get('basic').get(flag):
            curr_skills = [skill] if flag == flag2 else []
            if skill.get('type') == "passive":
                continue
            if not skill.get("ruby"):
                # Probably a skill triggered by another skill, try to find that skill
                triggering_skills = get_triggering_skills(skill.get("id"), flag2, region)
                if len(triggering_skills) > 0:
                    if flag == flag2:
                        curr_skills.extend(triggering_skills)
                    else:
                        curr_skills = triggering_skills
                else:
                    continue

            for curr_skill in curr_skills:
                servants = curr_skill.get('reverse').get('basic').get('servant')
                servant_found = False
                for servant in servants:
                    if (not servant.get('name') or
                                servant.get('type') == "servantEquip" or
                                servant.get('type') == "enemy" or
                                servant.get("collectionNo") == 0
                            ):
                        continue
                    servant_found = True
                if servant_found:
                    found_skills.append(curr_skill)
    return found_skills


def get_nps_with_trait(trait: str, region: str = "JP"):
    url = f"https://api.atlasacademy.io/basic/{region}/NP/search?svalsContain={trait}&reverse=true&lang=en"
    response = session.get(url)
    nps = json.loads(response.text)
    return nps


def get_triggering_skills(id: int, flag: str = "skill", region: str = "JP"):
    response = session.get(
        f"https://api.atlasacademy.io/basic/{region}/{flag}/search?reverse=true&reverseData=basic&svalsContain={id}&lang=en")
    return json.loads(response.text)


def get_np_chargers(sval_value: int = 5000, class_name: str = "", region: str = "JP"):
    np_charge_functions = get_functions(type="gainNp", region=region)
    np_charge_functions_self = []
    np_charge_functions_exceptself = []
    for function in np_charge_functions:
        if function.get("funcTargetType") == "self":
            np_charge_functions_self.append(function)
        elif "enemy" in function.get("funcTargetType"):
            continue
        else:
            np_charge_functions_exceptself.append(function)

    np_charge_skills_self = get_skills_from_functions(functions=np_charge_functions_self, flag="skill", region=region)
    np_charge_skills_exceptself = get_skills_from_functions(functions=np_charge_functions_exceptself, flag="skill", region=region)


    servants_self = []
    servants_exceptself = []
    for skill_self in np_charge_skills_self:
        servants_self.extend(skill_self.get('reverse').get('basic').get('servant'))
    for skill_exceptself in np_charge_skills_exceptself:
        servants_exceptself.extend(skill_exceptself.get('reverse').get('basic').get('servant'))
    
    servants_self = [servant for servant in servants_self if servant.get("collectionNo") != 0]
    servants_exceptself = [servant for servant in servants_exceptself if servant.get("collectionNo") != 0]

    if class_name:
        servants_self = [servant for servant in servants_self if servant.get("className") == class_name]
        servants_exceptself = [servant for servant in servants_exceptself if servant.get("className") == class_name]

    servants_self = remove_duplicates(servants_self)
    servants_exceptself = remove_duplicates(servants_exceptself)

    servants_self_aoe = []
    servants_self_st = []
    servants_self_other = []

    for servant in servants_self:
        servant_details = get_servant_by_id(session, servant.get("id"), region, False)
        total_sval = get_total_sval(servant_details, True)
        if total_sval < sval_value:
            continue

        nps = servant_details.get("noblePhantasms")
        if not nps or len(nps) == 0:
            continue

        effectFlags = nps[0].get("effectFlags")
        if "attackEnemyAll" in effectFlags:
            servants_self_aoe.append({ "totalSvals": total_sval, "details": servant_details })
        elif "attackEnemyOne" in effectFlags:
            servants_self_st.append({ "totalSvals": total_sval, "details": servant_details })
        else:
            servants_self_other.append({ "totalSvals": total_sval, "details": servant_details })

    servants_exceptself_aoe = []
    servants_exceptself_st = []
    servants_exceptself_other = []
    
    for servant in servants_exceptself:
        servant_details = get_servant_by_id(session, servant.get("id"), region, False)
        total_sval = get_total_sval(servant_details, False)
        if total_sval < sval_value:
            continue

        nps = servant_details.get("noblePhantasms")
        if not nps or len(nps) == 0:
            continue

        effectFlags = nps[0].get("effectFlags")
        if "attackEnemyAll" in effectFlags:
            servants_exceptself_aoe.append({ "totalSvals": total_sval, "details": servant_details })
        elif "attackEnemyOne" in effectFlags:
            servants_exceptself_st.append({ "totalSvals": total_sval, "details": servant_details })
        else:
            servants_exceptself_other.append({ "totalSvals": total_sval, "details": servant_details })

    return {
        "selfAoe": servants_self_aoe,
        "selfSt": servants_self_st,
        "selfOther": servants_self_other,
        "allyAoe": servants_exceptself_aoe,
        "allySt": servants_exceptself_st,
        "allyOther": servants_exceptself_other,
    }


def get_total_sval(servant, is_self: bool):
    total_sval = 0
    if not servant:
        return total_sval

    servant_skills = servant.get("skills")

    def key_func(s):
        return s["num"]

    servant_skills = sorted(servant_skills, key=key_func)
    for key, servant_skill_group in groupby(servant_skills, key=key_func):
        grouped_skills = list(servant_skill_group)
        servant_skill = grouped_skills[-1]

        for function in servant_skill.get("functions"):
            if function.get("funcType") != "gainNp":
                continue
            if "enemy" in function.get("funcTargetType"):
                continue
            functvals = function.get("functvals")
            if functvals and len(functvals) > 0:
                continue
            if is_self and function.get("funcTargetType") == "self":
                total_sval += function.get("svals")[-1].get("Value")
            if not is_self and not function.get("funcTargetType") == "self":
                total_sval += function.get("svals")[-1].get("Value")
    return total_sval


def remove_duplicates(list):
    return [i for n, i in enumerate(list) if i not in list[n + 1:]]
