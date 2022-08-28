# FGO Discord Bot

A discord bot for looking up FGO info from [Atlas Academy API](https://api.atlasacademy.io/rapidoc)
* Servant info
* NP/Skills search by traits, target
* Current weekly missions
* Calculate gacha chance
* List NP chargers

[Bot Invite Link](https://discord.com/api/oauth2/authorize?client_id=1005691850834837584&permissions=1024&scope=bot%20applications.commands)

When developing, use your own env.config file or set TOKEN in the environment variables
```
[Auth]
TOKEN=<your token here>
DATABASE_URL=<PostgresDB URL>
SCOPES=<Discord Guild IDs. Can be empty>
```
## Commands
### /servant
Gets servant info

### /missions
Gets current weekly missions.
Also shows the most optimal way to complete them (Free quests only).

### /drops
Finds drop location for materials

### /np-chargers
Lists the NP chargers

### /search
Search for a skill or NP that meets the criteria

### /gacha
Gacha probability calculation
