import requests_cache
import json

session = None

def init_session(_session: requests_cache.CachedSession):
    global session
    if not session:
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
    url = f"https://api.atlasacademy.io/basic/{region}/buff/search?reverse=true&reverseDepth=servant&reverseData=basic&{buff_query}{trait_query}"
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
    url = f"https://api.atlasacademy.io/basic/{region}/function/search?reverse=true&reverseDepth=servant{type_query}{target_query}{trait_query}"
    response = session.get(url)
    functions = json.loads(response.text)

    if trait:
        # tvals and vals are both traits
        url = f"https://api.atlasacademy.io/basic/{region}/function/search?reverse=true&reverseDepth=servant{type_query}{target_query}{trait_query2}"
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
                                servant.get('type') == "enemy"
                            ):
                        continue
                    servant_found = True
                if servant_found:
                    found_skills.append(curr_skill)
    return found_skills


def get_nps_with_trait(trait: str, region: str = "JP"):
    url = f"https://api.atlasacademy.io/basic/{region}/NP/search?svalsContain={trait}&reverse=true"
    response = session.get(url)
    nps = json.loads(response.text)
    return nps


def get_triggering_skills(id: int, flag: str = "skill", region: str = "JP"):
    response = session.get(
        f"https://api.atlasacademy.io/basic/{region}/{flag}/search?reverse=true&reverseData=basic&svalsContain={id}")
    return json.loads(response.text)