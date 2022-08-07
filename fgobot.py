import configparser
import requests
import json
import interactions

configparser = configparser.ConfigParser()
configparser.read('env.config')
token = configparser.get('Auth', 'TOKEN')
bot = interactions.Client(token=token)

def get_servant(name):
    response = requests.get("https://api.atlasacademy.io/nice/JP/servant/search?name=" + name)
    json_data = json.loads(response.text)
    skill1 = json_data[0].get('skills')[0].get('name')
    skill1desc = json_data[0].get('skills')[0].get('detail')
    skill2 = json_data[0].get('skills')[1].get('name')
    skill2desc = json_data[0].get('skills')[1].get('detail')
    skill3 = json_data[0].get('skills')[2].get('name')
    skill3desc = json_data[0].get('skills')[2].get('detail')
    embed = interactions.Embed(
        title="Servant Info",
        description="",
        color=interactions.Color.black()
    )
    embed.set_thumbnail(
        url=json_data[0]
            .get('extraAssets')
            .get('faces')
            .get('ascension')
            .get('1')
    )

    embed.add_field("Name", json_data[0].get('name'))
    embed.add_field("Rarity", "★"*json_data[0].get('rarity'))
    embed.add_field("Class", json_data[0].get('className'))
    embed.add_field(f"Skill 1: {skill1}", skill1desc);
    embed.add_field(f"Skill 2: {skill2}", skill2desc);
    embed.add_field(f"Skill 3: {skill3}", skill3desc);

    return embed

def get_skill_with_type(type: str):
    if type == "": return []
    url = f"https://api.atlasacademy.io/basic/JP/function/search?reverse=true&reverseDepth=servant&type={type}&targetType=self"
    found_skills = []
    response = requests.get(url)
    functions = json.loads(response.text)
    for function in functions:
        for skill in function.get('reverse').get('basic').get('skill'):
            if skill.get('name') == "": continue
            servants = skill.get('reverse').get('basic').get('servant')
            servant_found = False
            for servant in servants:
                if servant.get('name') == "" or servant.get('type') == "servantEquip":
                    continue
                servant_found = True
            if servant_found:
                found_skills.append(skill)
    return found_skills

def get_skill(type: str, type2: str = ""):
    found_list_1 = get_skill_with_type(type)
    found_list_2 = get_skill_with_type(type2)
    matched_skills_list = []
    result_str = [f"type: {type}, type2: {type2}\n"]
    if len(found_list_2) > 0:
        for element in found_list_1:
            if element in found_list_2:
                matched_skills_list.append(element)
    else:
        matched_skills_list = found_list_1
    
    for skill in matched_skills_list:
        result_str.append(f"・{skill.get('name')}\n")
        servants = skill.get('reverse').get('basic').get('servant')
        servantList = []
        for servant in servants:
            if servant.get('name') == "" or servant.get('type') == "servantEquip":
                continue
            servant_str = f"  └{servant.get('name')} {servant.get('className')}\n"
            if servant_str not in servantList:
                servantList.append(servant_str)
                result_str.append(servant_str)

    if len(result_str) > 0:
        return "".join(result_str[0:20])
    else:
        return "Not found."

@bot.command(
    scope=[760776452609802250,450114606669496320],
)
@interactions.option(str, name="name", description="Servant name", required=True)
async def servant(ctx: interactions.CommandContext, name: str):
    await ctx.send(embeds=get_servant(name))

@bot.command(
    scope=[760776452609802250,450114606669496320],
)
@interactions.option(str, name="type", description="Skill type", required=True, autocomplete=True)
@interactions.option(str, name="type2", description="Skill type 2", required=False, autocomplete=True)
async def skill(ctx: interactions.CommandContext, type: str, type2: str = ""):
    print(type + type2)
    await ctx.send(get_skill(type, type2))

def populateSkillNamesList(input_value: str):
    options = "none ┃ addState ┃ subState ┃ damage ┃ damageNp ┃ gainStar ┃ gainHp ┃ gainNp ┃ lossNp ┃ shortenSkill ┃ extendSkill ┃ releaseState ┃ lossHp ┃ instantDeath ┃ damageNpPierce ┃ damageNpIndividual ┃ addStateShort ┃ gainHpPer ┃ damageNpStateIndividual ┃ hastenNpturn ┃ delayNpturn ┃ damageNpHpratioHigh ┃ damageNpHpratioLow ┃ cardReset ┃ replaceMember ┃ lossHpSafe ┃ damageNpCounter ┃ damageNpStateIndividualFix ┃ damageNpSafe ┃ callServant ┃ ptShuffle ┃ lossStar ┃ changeServant ┃ changeBg ┃ damageValue ┃ withdraw ┃ fixCommandcard ┃ shortenBuffturn ┃ extendBuffturn ┃ shortenBuffcount ┃ extendBuffcount ┃ changeBgm ┃ displayBuffstring ┃ resurrection ┃ gainNpBuffIndividualSum ┃ setSystemAliveFlag ┃ forceInstantDeath ┃ damageNpRare ┃ gainNpFromTargets ┃ gainHpFromTargets ┃ lossHpPer ┃ lossHpPerSafe ┃ shortenUserEquipSkill ┃ quickChangeBg ┃ shiftServant ┃ damageNpAndCheckIndividuality ┃ absorbNpturn ┃ overwriteDeadType ┃ forceAllBuffNoact ┃ breakGaugeUp ┃ breakGaugeDown ┃ moveToLastSubmember ┃ expUp ┃ qpUp ┃ dropUp ┃ friendPointUp ┃ eventDropUp ┃ eventDropRateUp ┃ eventPointUp ┃ eventPointRateUp ┃ transformServant ┃ qpDropUp ┃ servantFriendshipUp ┃ userEquipExpUp ┃ classDropUp ┃ enemyEncountCopyRateUp ┃ enemyEncountRateUp ┃ enemyProbDown ┃ getRewardGift ┃ sendSupportFriendPoint ┃ movePosition ┃ revival ┃ damageNpIndividualSum ┃ damageValueSafe ┃ friendPointUpDuplicate ┃ moveState ┃ changeBgmCostume ┃ func126 ┃ func127 ┃ updateEntryPositions ┃ buddyPointUp ┃ addFieldChangeToField ┃ subFieldBuff".split(" ┃ ")
    filteredOptions = [option for option in options if input_value.upper() in option.upper()]
    choices = []
    for option in filteredOptions[0:24]:
        choices.append(interactions.Choice(name=option, value=option))
    return choices

@bot.autocomplete(command="skill", name="type")
async def autocomplete_choice_list(ctx: interactions.CommandContext, type: str = ""):
    await ctx.populate(populateSkillNamesList(type))

@bot.autocomplete(command="skill", name="type2")
async def autocomplete_choice_list(ctx: interactions.CommandContext, type2: str = ""):
    await ctx.populate(populateSkillNamesList(type2))

bot.start()
