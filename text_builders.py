import requests_cache
import json
import re
from enum import Flag
import fgo_api_types.enums as enums

SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

class NpFunctionType(Flag):
    LEVEL = 1
    OVERCHARGE = 2
    BOTH = LEVEL | OVERCHARGE
    NONE = 4


def get_np_function_type(function) -> NpFunctionType:
    svals = function.get("svals")
    svals2 = function.get("svals2")
    if (
        (
            svals[0].get("Value") != svals[1].get("Value") or
            svals[0].get("Correction") != svals[1].get("Correction") or
            svals[0].get("Rate") != svals[1].get("Rate")
        )
         and
        (
            svals[0].get("Value") != svals2[0].get("Value") or
            svals[0].get("Correction") != svals2[0].get("Correction") or
            svals[0].get("Rate") != svals2[0].get("Rate")
        )
    ):
        return NpFunctionType.BOTH

    if (
        svals[0].get("Value") != svals[1].get("Value") or
        svals[0].get("Correction") != svals[1].get("Correction") or
        svals[0].get("Rate") != svals[1].get("Rate")
    ):
        return NpFunctionType.LEVEL
    
    if (
        svals[0].get("Value") != svals2[0].get("Value") or
        svals[0].get("Correction") != svals2[0].get("Correction") or
        svals[0].get("Rate") != svals2[0].get("Rate")
    ):
        return NpFunctionType.OVERCHARGE
    
    return NpFunctionType.NONE


def get_skill_description(session: requests_cache.CachedSession, skill, sub_skill: bool = False, region: str = "JP"):
    skill_descs = []
    if not sub_skill and skill.get("coolDown"): skill_descs.append(f'**Base Cooldown: ** {skill.get("coolDown")[0]}')
    is_np = False
    if skill.get("card"): is_np = True # Noble phantasms
    funcIdx = 0
    for function in skill.get("functions"):
        if function.get("funcTargetTeam") == "enemy": continue
        func_type = function.get("funcType")
        if func_type == "none": continue

        svals_level = function.get("svals")
        sval_rate = svals_level[0].get("Rate")
        sval_turns = svals_level[0].get("Turn")
        sval_count = svals_level[0].get("Count")
        sval_value = svals_level[0].get("Value")
        sval_value2 = svals_level[0].get("Value2")
        sval_userate = svals_level[0].get("UseRate")
        sval_target = svals_level[0].get("Target")
        sval_targetlist = svals_level[0].get("TargetList")
        sval_starhigher = svals_level[0].get("StarHigher")
        sval_correction = svals_level[0].get("Correction")
        svals_overcharge = [svals_level[0]]
        if is_np: svals_overcharge = [
            function.get("svals")[0],
            function.get("svals2")[0],
            function.get("svals3")[0],
            function.get("svals4")[0],
            function.get("svals5")[0],
        ]

        chances_text = ""
        values_text = ""
        extra_values_text = ""
        turns_text = ""
        count_text = ""
        usechance_text = ""
        supereffective_target = ""
        target_vals_text = ""

        np_function_type = NpFunctionType.NONE
        if is_np: np_function_type = get_np_function_type(function)
        
        func_tvals = function.get("functvals")
        if func_tvals:
            target_traits = []
            for tval in func_tvals:
                if int(tval.get("id")) >= 5000: continue
                target_traits.append(get_trait_desc(tval.get("id")))
            target_vals_text = f' with trait [{", ".join(target_traits)}]'

        buff_type = function.get("buffs")[0].get("type") if function.get("buffs") and len(function.get("buffs")) > 0 else ""
        is_single_value = False
        if sval_value:
            valuesTextList = []
            if buff_type.endswith("Function"):
                func_skill = get_skill_by_id(session, sval_value)
                func_skill_desc = get_skill_description(session=session, skill=func_skill, sub_skill=True, region=region)
                values_text += func_skill_desc
            elif all(sval.get("Value") == svals_level[0].get("Value") for sval in svals_level):
                # All values stay the same on NP level up
                if is_np and NpFunctionType.OVERCHARGE in np_function_type:
                    values_text = get_overcharge_values(function, buff_type, func_type)
                else:
                    is_single_value = True
                    if buff_type == "addIndividuality": # Add trait
                        values_text = f'{get_trait_desc(svals_level[0].get("Value"), region)}'
                    elif buff_type == "fieldIndividuality": # Change fields
                        values_text = f'{get_trait_desc(svals_level[0].get("Value"), region)}'
                    else:
                        values_text = f'{get_sval_from_buff(svals_level[0].get("Value"), buff_type, func_type)}'
                
                if is_np:
                    # For servants with correction (supereffective dmg) or chance increase on NP level up instead of NP damage (e.g. Euryale)
                    if not all(sval.get("Correction") == sval_correction for sval in svals_level):
                        for svalIdx, sval in enumerate(svals_level):
                            valuesTextList.append(f'{get_sval_from_buff(sval.get("Correction"), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
                        np_text = " (Level)" if is_np and NpFunctionType.LEVEL in np_function_type else ""
                        extra_values_text = f'Value{np_text}: {" · ".join(valuesTextList)}'
                    elif not all(sval.get("Rate") == svals_level[0].get("Rate") for sval in svals_level):
                        for svalIdx, sval in enumerate(svals_level):
                            valuesTextList.append(f'{get_sval_from_buff(sval.get("Rate"), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
                        np_text = " (Level)" if is_np and NpFunctionType.LEVEL in np_function_type else ""
                        extra_values_text = f'Chance{np_text}: {" · ".join(valuesTextList)}'
            else:
                for svalIdx, sval in enumerate(svals_level):
                    valuesTextList.append(f'{get_sval_from_buff(sval.get("Value"), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
                np_text = " (Level)" if is_np and NpFunctionType.LEVEL in np_function_type else ""
                values_text = f'Value{np_text}: {" · ".join(valuesTextList)}'
            if is_np:
                if sval_target and func_type == "damageNpIndividual":
                        supereffective_target = get_trait_desc(sval_target, region)
                if sval_targetlist and func_type == "damageNpIndividualSum":
                    supereffective_target = get_trait_desc(sval_targetlist[0], region)
                    
        else:
            if buff_type == "counterFunction":
                # Bazett
                counter_id = svals_level[0].get("CounterId")
                func_skill = get_np_by_id(session, counter_id, region)
                func_skill_desc = get_skill_description(session=session, skill=func_skill, sub_skill=True, region=region)
                values_text += func_skill_desc

        is_multiple_rates = False
        if is_np:
            is_multiple_rates = (
                # Changes on NP level or overcharge
                not all(sval.get("Rate") == svals_level[0].get("Rate") for sval in svals_overcharge)
                or not all(sval.get("Rate") == svals_level[0].get("Rate") for sval in svals_level)
            )
        if sval_rate and (abs(sval_rate) != 1000 or is_multiple_rates) and abs(sval_rate) != 5000: # Skip 100% chance and 500% chance
            chances_list = []
            if all(sval.get("Rate") == svals_level[0].get("Rate") for sval in svals_level):
                # Chance stays the same on NP level up => Overcharge or single value
                if NpFunctionType.OVERCHARGE in np_function_type:
                    chances_text = get_overcharge_values(function, buff_type, func_type, "Rate", "Chance")
                else:
                    chances_text = f'Chance: {remove_zeros_decimal(svals_level[0].get("Rate") / 10)}%'
            else:
                # Chance changes on NP level up (e.g. Stheno)
                for svalIdx, sval in enumerate(svals_level):
                    chances_list.append(f'{remove_zeros_decimal(sval.get("Rate") / 10)}{str(svalIdx + 1).translate(SUB)}%')
                np_text = " (Level)" if is_np and NpFunctionType.LEVEL in np_function_type else ""
                chances_text = f'Chance{np_text}: {" · ".join(chances_list)}'

        if sval_userate and sval_userate != 1000 and sval_userate != 5000:
            usechances_list = []
            if all(sval.get("UseRate") == svals_level[0].get("UseRate") for sval in svals_level):
                usechance_text = f'Chance: {remove_zeros_decimal(svals_level[0].get("UseRate") / 10)}%'
            else:
                for svalIdx, sval in enumerate(svals_level):
                    usechances_list.append(f'{remove_zeros_decimal(sval.get("UseRate") / 10)}%{str(svalIdx + 1).translate(SUB)}%')
                usechance_text = f'Chance: {" · ".join(usechances_list)}'

        if sval_count and sval_count > 0:
            count_text = f'{sval_count} Time{"s" if sval_count > 1 else ""}'
        if sval_turns and sval_turns > 0:
            turns_text = f'{sval_turns} Turn{"s" if sval_turns > 1 else ""}'

        turns_count_text = ", ".join([count_text, turns_text]).strip(", ")
        if turns_count_text: turns_count_text = f"({turns_count_text})"
        
        function_effect = func_desc_dict.get(func_type)
        if not function_effect: function_effect = title_case(func_type)
        inline_value_text = f" ({values_text})" if is_single_value else ""

        sub_skill_text = "└Sub-" if sub_skill else ""

        is_negative_rate = sval_rate and sval_rate == -5000
        previous_function_text = "If previous function succeeds, " if is_negative_rate else ""

        if sval_starhigher and sval_starhigher > 0:
            previous_function_text = f"[{sval_starhigher}+ Stars] " + previous_function_text
        
        func_target_text = title_case(target_desc_dict.get(function.get("funcTargetType")))
        if not func_target_text: func_target_text = title_case(function.get("funcTargetType"))
        if func_type.startswith("damageNpIndividualSum"):
            # Taira no Kagekiyo
            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} to [{func_target_text}] with {remove_zeros_decimal(sval_correction / 10)}% bonus damage for each [{supereffective_target}] on the field (Max {svals_level[0].get("ParamAddMaxCount")})')
        elif func_type.startswith("damageNpIndividual"):
            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} to [{func_target_text}] with bonus damage to [{supereffective_target}]')
        elif func_type.startswith("damageNp"):
            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} to [{func_target_text}]')
        elif func_type.startswith("addState"):
            buff_text = ""
            if buff_type == "donotAct":
                for val in function.get("buffs")[0].get("vals"):
                    buff_text = stun_type_dict.get(str(val.get("id")))
                    if buff_text: break
            else:
                buff_text = buff_desc_dict.get(buff_type)

            if not buff_text: buff_text = title_case(buff_type)
            function_effect = f'Grants [{buff_text}]'

            func_quest_tvals = function.get("funcquestTvals") # Fields
            if func_quest_tvals:
                target_traits = []
                for tval in func_quest_tvals:
                    target_traits.append(get_trait_desc(tval.get("id"), region))
                if len(target_traits) > 0: function_effect += f' on [{", ".join(target_traits)}]'

            ck_self_indv = function.get("buffs")[0].get("ckSelfIndv") # Cards
            if ck_self_indv:
                target_traits = []
                for ck in ck_self_indv:
                    target_traits.append(title_case(ck.get("name")))
                if len(target_traits) > 0: function_effect += f' to [{", ".join(target_traits)}]'
            
            ck_op_indv = function.get("buffs")[0].get("ckOpIndv") # Atk bonus for trait
            if ck_op_indv:
                target_traits = []
                for ck in ck_op_indv:
                    if int(ck.get("id")) < 3000:
                        trait_desc = get_trait_desc(ck.get("id"), region)
                    else:
                        trait_desc = title_case(ck.get("name"))
                    target_traits.append(trait_desc)
                if len(target_traits) > 0: function_effect += f' against [{", ".join(target_traits)}]'

            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} to [{func_target_text}]{target_vals_text} {turns_count_text}')
        elif func_type == "gainNpBuffIndividualSum":
            traitvals = function.get("traitVals")
            traitvals_text = []
            for tval in traitvals:
                if int(tval.get("id")) >= 5000: continue
                traitvals_text.append(get_trait_desc(tval.get("id")))
            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} [{", ".join(traitvals_text)}] to [{func_target_text}]{target_vals_text} {turns_count_text}')
        elif func_type == "moveState":
            # Lady Avalon, Van Gogh, ...
            depend_func_id = svals_level[0].get("DependFuncId")
            depend_func = get_function_by_id(session, depend_func_id, region)
            traitvals = depend_func.get("traitVals")
            traitvals_text = []
            for tval in traitvals:
                if int(tval.get("id")) >= 5000: continue
                traitvals_text.append(get_trait_desc(tval.get("id")))
            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} [{", ".join(traitvals_text)}] to [{func_target_text}]{target_vals_text} {turns_count_text}')
        elif func_type == "subState":
            # Remove effects
            remove_text = f' ({sval_value2} effect{"s" if sval_value2 > 1 else ""})' if sval_value2 else ""

            traitvals = function.get("traitVals")
            traitvals_text = []
            for tval in traitvals:
                if int(tval.get("id")) >= 5000: continue
                traitvals_text.append(get_trait_desc(tval.get("id")))
            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} [{", ".join(traitvals_text)}]{remove_text} from [{func_target_text}]{target_vals_text} {turns_count_text}')
        else:
            skill_descs.append(f'**{sub_skill_text}Effect {funcIdx + 1}**: {previous_function_text}{function_effect}{inline_value_text} to [{func_target_text}]{target_vals_text} {turns_count_text}')

        if chances_text: skill_descs.append(f'{chances_text}')
        if usechance_text: skill_descs.append(f'{usechance_text}')
        if values_text and not is_single_value: skill_descs.append(f'{values_text}')
        if extra_values_text: skill_descs.append(f'{extra_values_text}')
        funcIdx += 1
    return "\n".join(skill_descs)


def get_overcharge_values(function, buff_type, func_type, key: str = "Value", prepend_text: str = "Value"):
    valuesTextList = []
    for svalIdx, sval in enumerate([
        function.get("svals")[0],
        function.get("svals2")[0],
        function.get("svals3")[0],
        function.get("svals4")[0],
        function.get("svals5")[0],
    ]):
        valuesTextList.append(f'{get_sval_from_buff(sval.get(key), buff_type, func_type)}{str(svalIdx + 1).translate(SUB)}')
    values_text = f'{prepend_text} (Overcharge): {" - ".join(valuesTextList)}'
    return values_text


def get_sval_from_buff(value: int, buff_type: str, func_type: str) -> str:
    if not buff_type:
        if func_type.startswith("gainNp"):
            return f'{remove_zeros_decimal(value / 100)}%'
        elif func_type.startswith("damageNp"):
            return f'{remove_zeros_decimal(value / 10)}%'
        elif func_type == "lossNp":
            return f'{remove_zeros_decimal(value / 100)}%'
    if buff_type == "upChagetd":
        return remove_zeros_decimal(value)
    if buff_type.startswith("up") or buff_type.startswith("down"):
        return f'{remove_zeros_decimal(value / 10)}%'
    if buff_type.startswith("regainNp"):
        return f'{remove_zeros_decimal(value / 100)}%'
    if buff_type.startswith("donotAct"):
        return f'{remove_zeros_decimal(value / 10)}%'
    return remove_zeros_decimal(value)


def remove_zeros_decimal(value):
    return str(abs(value)).rstrip("0").rstrip(".") if "." in str(value) else str(value)


def title_case(string):
    if not string:
        return string
    words = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', string)).split()
    if len(words) > 0:
        words[0] = words[0][0].upper() + words[0][1:]
    return " ".join(words)


def get_trait_desc(trait_id: str | int, region: str = "JP"):
    trait = enums.TRAIT_NAME.get(int(trait_id))
    trait_name = title_case(trait.value if trait else "unknown")
    if str(trait_id).startswith("4"):
        # Cards
        return trait_name
    url = f'https://apps.atlasacademy.io/db/{region}/entities?trait={trait_id}'
    return f'[{trait_name}]({url})'


def get_function_by_id(session: requests_cache.CachedSession, id: int, region: str = "JP"):
    """Get function by ID

    Args:
        id (int): Function ID
        region (str, optional): Region. Defaults to "JP".

    Returns:
        Function object
    """
    response = session.get(
        f"https://api.atlasacademy.io/nice/{region}/function/{id}?lang=en")
    function = json.loads(response.text)
    if function.get('detail') == "Function not found":
        return None
    else:
        return function


def get_skill_by_id(session: requests_cache.CachedSession, id: int, region: str = "JP"):
    """Get skill by ID

    Args:
        id (int): Skill ID
        region (str, optional): Region. Defaults to "JP".

    Returns:
        Skill object
    """
    response = session.get(
        f"https://api.atlasacademy.io/nice/{region}/skill/{id}?lang=en")
    skill = json.loads(response.text)
    if skill.get('detail') == "Skill not found":
        return None
    else:
        return skill


def get_np_by_id(session: requests_cache.CachedSession, id: int, region: str = "JP"):
    """Get NP by ID

    Args:
        id (int): NP ID
        region (str, optional): Region. Defaults to "JP".

    Returns:
        Skill object
    """
    response = session.get(
        f"https://api.atlasacademy.io/nice/{region}/NP/{id}?lang=en")
    skill = json.loads(response.text)
    if skill.get('detail') == "NP not found":
        return None
    else:
        return skill


def get_servant_by_id(session, id: int, region: str = "JP", lore: bool = True):
    """Get servant by ID

    Args:
        id (int): Servant ID
        region (str, optional): Region. Defaults to "JP".

    Returns:
        Servant object
    """
    response = session.get(
        f'https://api.atlasacademy.io/nice/{region}/svt/{id}?lore={"true" if lore else "false"}&lang=en')
    servant = json.loads(response.text)
    if servant.get('detail') == "Svt not found":
        return None
    else:
        return servant


def get_enums(enum_type: str):
    return enums.ALL_ENUMS.get(enum_type)


def get_traits():
    return { str(id): trait.value for id, trait in enums.TRAIT_NAME.items()}


func_desc_dict = {
    "absorbNpturn": "Absorb NP Charge (Enemy)",
    "addState": "Apply Buff",
    "addStateShort": "Apply Buff (short)",
    "cardReset": "Shuffle Cards",
    "changeBgmCostume": "Change BGM",
    "damageNp": "Deal Damage",
    "damageNpHpratioLow": "Deal Damage with Bonus for Low Health",
    "damageNpIndividual": "Deal Damage with Bonus to Trait",
    "damageNpIndividualSum": "Deal Damage with Bonus per Trait",
    "damageNpPierce": "Deal Damage that pierces defense",
    "damageNpRare": "Deal Damage with Bonus to Rarity",
    "damageNpStateIndividualFix": "Deal Damage with Bonus to Trait",
    "damageNpCounter": "Reflect Damage Received",
    "damageValue": "Deal Damage",
    "delayNpturn": "Drain Charge",
    "eventDropUp": "Increase Event Drop Amount",
    "eventPointUp": "Increase Event Point",
    "eventDropRateUp": "Increase Event Drop Rate",
    "eventPointRateUp": "Increase Event Point Rate",
    "enemyEncountCopyRateUp": "Create Clone of Enemy",
    "enemyEncountRateUp": "Improve Appearance Rate of Enemy",
    "expUp": "Increase Master Exp",
    "extendSkill": "Increase Cooldowns",
    "fixCommandcard": "Lock Command Cards",
    "friendPointUp": "Increase Friend Point",
    "friendPointUpDuplicate": "Increase Friend Point (stackable)",
    "forceInstantDeath": "Force Instant Death",
    "gainHp": "Restore HP",
    "gainHpFromTargets": "Absorb HP",
    "gainHpPer": "Restore HP to Percent",
    "gainNp": "Charge NP",
    "gainNpBuffIndividualSum": "Charge NP per Trait",
    "gainNpFromTargets": "Absorb NP Charge",
    "gainStar": "Gain Critical Stars",
    "hastenNpturn": "Increase Charge",
    "instantDeath": "Apply Death",
    "lossHp": "Drain HP",
    "lossHpSafe": "Drain HP without killing",
    "lossNp": "Drain NP",
    "lossStar": "Remove Critical Stars",
    "moveState": "Move Effects",
    "moveToLastSubmember": "Move to last reserve slot",
    "none": "No Effect",
    "qpDropUp": "Increase QP Reward",
    "qpUp": "Increase QP Reward",
    "replaceMember": "Swap members",
    "servantFriendshipUp": "Increase Bond Gain",
    "shortenSkill": "Reduce Cooldowns",
    "subState": "Remove Effects",
    "userEquipExpUp": "Increase Mystic Code Exp",
    "func126": "Remove Command Spell",
    "addFieldChangeToField": "Change Field",
    "subFieldBuff": "Remove Field Buff",
}

buff_desc_dict = {
    "addMaxhp": "Max HP Up",
    "subMaxhp": "Max HP Down",
    "upAtk": "ATK Up",
    "downAtk": "ATK Down",
    "upChagetd": "Overcharge Up",
    "upCommandall": "Card Up",
    "downCommandall": "Card Down",
    "upCommandatk": "ATK Up",
    "downCommandatk": "ATK Down",
    "upCriticaldamage": "Critical Damage Up",
    "downCriticaldamage": "Critical Damage Down",
    "upCriticalpoint": "Star Drop Rate Up",
    "downCriticalpoint": "Star Drop Rate Down",
    "upCriticalrate": "Critical Rate Up",
    "downCriticalrate": "Critical Rate Down",
    "upCriticalRateDamageTaken": "Chance of Receiving Critical Attack Up",
    "downCriticalRateDamageTaken": "Chance of Receiving Critical Attack Down",
    "upCriticalStarDamageTaken": "Attacker Star Drop Rate Up",
    "downCriticalStarDamageTaken": "Attacker Star Drop Rate Down",
    "upDamage": "SP.DMG Up",
    "downDamage": "SP.DMG Down",
    "upDamageIndividualityActiveonly": "SP.DMG Up",
    "downDamageIndividualityActiveonly": "SP.DMG Down",
    "upDamageEventPoint": "SP.DMG Up",
    "upDamagedropnp": "NP Gain When Damaged Up",
    "downDamagedropnp": "NP Gain When Damaged Down",
    "upDefence": "DEF Up",
    "downDefence": "DEF Down",
    "upDefencecommandall": "Resistance Up",
    "downDefencecommandall": "Resistance Down",
    "upDropnp": "NP Gain Up",
    "downDropnp": "NP Gain Down",
    "upGainHp": "Received Healing Up",
    "downGainHp": "Received Healing Down",
    "upGivegainHp": "Healing Dealt Up",
    "downGivegainHp": "Healing Dealt Down",
    "upFuncHpReduce": "DoT Effectiveness Up",
    "downFuncHpReduce": "DoT Effectiveness Down",
    "upGrantInstantdeath": "Death Chance Up",
    "downGrantInstantdeath": "Death Chance Down",
    "upResistInstantdeath": "Death Resist Up",
    "upGrantstate": "Casted Effect Chance Up",
    "downGrantstate": "Casted Effect Chance Down",
    "upNonresistInstantdeath": "Death Resist Down",
    "upNpdamage": "NP Damage Up",
    "downNpdamage": "NP Damage Down",
    "upSpecialdefence": "SP.DEF Up",
    "downSpecialdefence": "SP.DEF Down",
    "upDamageSpecial": "Attack Special Damage Up",
    "upStarweight": "Star Weight Up",
    "downStarweight": "Star Weight Down",
    "downTolerance": "Received Effect Chance Up",
    "upTolerance": "Received Effect Chance Down",
    "upToleranceSubstate": "Buff Removal Resistance Up",
    "downToleranceSubstate": "Buff Removal Resistance Down",
    "buffRate": "Buff Effectiveness Up",
    "avoidInstantdeath": "Immune to Death",
    "avoidState": "Immunity",
    "addDamage": "Damage Plus",
    "addIndividuality": "Add Trait",
    "avoidance": "Evade",
    "avoidanceIndividuality": "Evade",
    "changeCommandCardType": "Change Command Card Types",
    "commandcodeattackFunction": "Command Code Effect",
    "commandcodeattackAfterFunction": "Command Code After Effect",
    "breakAvoidance": "Sure Hit",
    "delayFunction": "Trigger Skill after Duration",
    "donotAct": "Unable to Act",
    "donotNoble": "NP Seal",
    "donotNobleCondMismatch": "NP Block if Condition Failed",
    "donotRecovery": "Recovery Disabled",
    "donotReplace": "No Order Change",
    "donotSelectCommandcard": "Do Not Shuffle In Cards",
    "donotSkill": "Skill Seal",
    "donotSkillSelect": "Skill Seal",
    "fieldIndividuality": "Change Field Type",
    "fixCommandcard": "Freeze Command Cards",
    "guts": "Guts",
    "gutsFunction": "Trigger Skill on Guts",
    "gutsRatio": "Guts (Ratio)",
    "invincible": "Invincible",
    "multiattack": "Multiple Hits",
    "pierceInvincible": "Ignore Invincible",
    "pierceDefence": "Ignore DEF",
    "preventDeathByDamage": "Prevent death by damage",
    "reflectionFunction": "Trigger Skill on end of enemy's turn",
    "regainHp": "HP Per Turn",
    "regainNp": "NP Per Turn",
    "regainStar": "Stars Per Turn",
    "selfturnendFunction": "Trigger Skill every Turn",
    "specialInvincible": "Special invincible",
    "subSelfdamage": "Damage Cut",
    "tdTypeChange": "Change Noble Phantasm",
    "tdTypeChangeArts": "Set Noble Phantasm: Arts",
    "tdTypeChangeBuster": "Set Noble Phantasm: Buster",
    "tdTypeChangeQuick": "Set Noble Phantasm: Quick",
    "upHate": "Taunt",
    "upNpturnval": "Increase NP Gauge Gained Per Turn",
    "downNpturnval": "Reduce NP Gauge Gained Per Turn",
}

target_desc_dict = {
    "self": "self",
    "ptOne": "one party member",
    "ptAll": "party",
    "enemy": "one enemy",
    "enemyAll": "all enemies",
    "ptFull": "party (including reserve)",
    "enemyFull": "all enemies (including reserve)",
    "ptOther": "party except self",
    "ptOneOther": "another party member besides target",
    "ptRandom": "one random party member",
    "enemyOther": "other enemies besides target",
    "enemyRandom": "one random enemy",
    "ptOtherFull": "party except self (including reserve)",
    "enemyOtherFull": "other enemies (including reserve)",
    "ptselectOneSub": "active party member and reserve party member",
    "ptselectSub": "reserve party member",
    "ptOneAnotherRandom": "another random party member",
    "ptSelfAnotherRandom": "another random party member (except self)",
    "enemyOneAnotherRandom": "other random enemy",
    "ptSelfAnotherFirst": "first other party member (except self)",
    "ptSelfAnotherLast": "last other party member (except self)",
    "ptOneHpLowestValue": "party member with the lowest HP",
    "ptOneHpLowestRate": "party member with the lowest HP relative to their max HP",
    "commandTypeSelfTreasureDevice": "target noble phantasm version",
    "fieldOther": "party and enemies except self",
    "enemyOneNoTargetNoAction": "entity that last dealt damage to self",
}

stun_type_dict = {
    "3011": "Poison",
    "3012": "Charm",
    "3013": "Petrify",
    "3014": "Stun",
    "3015": "Burn",
    "3026": "Curse",
    "3045": "Bound",
    "3047": "Pigify",
    "3066": "Sleep",
}