#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import UnityPy

locales = [
	'deDE',
	'enUS',
	'esES',
	'esMX',
	'frFR',
	'itIT',
	'jaJP',
	'koKR',
	'plPL',
	'ptBR',
	'ruRU',
	'thTH',
	'zhCN',
	'zhTW',
]

local_state = {
	"total_handled": 0,
}


nodes_to_parse = [
	"ACCOUNT_LICENSE", 
	"ACHIEVE_CONDITION", 
	"ACHIEVE_REGION_DATA", 
	"ACHIEVE",
	"ACHIEVEMENT_CATEGORY",
	"ACHIEVEMENT_SECTION_ITEM", 
	"ACHIEVEMENT_SECTION",
	"ACHIEVEMENT_SUBCATEGORY", 
	"ACHIEVEMENT",
	"ADVENTURE_DATA",
	"ADVENTURE_DECK",
	"ADVENTURE_GUEST_HEROES", 
	"ADVENTURE_HERO_POWER",
	"ADVENTURE_LOADOUT_TREASURES",
	"ADVENTURE_MISSION",
	"ADVENTURE_MODE",
	"ADVENTURE",
	"BANNER", 
	"BATTLEGROUNDS_BOARD_SKIN",
	"BATTLEGROUNDS_EMOTE",
	"BATTLEGROUNDS_FINISHER",
	"BATTLEGROUNDS_GUIDE_SKIN",
	"BATTLEGROUNDS_HERO_SKIN", 
	"BATTLEGROUNDS_SEASON", 
	"BOARD",
	"BONUS_BOUNTY_DROP_CHANCE",
	"BOOSTER_CARD_SET", 
	"BOOSTER", 
	"BUILDING_TIER", 
	"CARD_ADDITONAL_SEARCH_TERMS",
	"CARD_BACK",
	"CARD_CHANGE", 
	"CARD_DISCOVER_STRING", 
	"CARD_EQUIPMENT_ALT_TEXT",
	"CARD_HERO", 
	"CARD_PLAYER_DECK_OVERRIDE",
	"CARD_SET_SPELL_OVERRIDE",
	"CARD_SET_TIMING",
	"CARD_SET", 
	"CARD_TAG", 
	"CARD",
	"CHARACTER_DIALOG_ITEMS", 
	"CHARACTER_DIALOG", 
	"CLASS_EXCLUSIONS",
	"CLASS", 
	"CLIENT_STRING",
	"COIN", 
	"CREDITS_YEAR",
	"DECK",
	"DECK_CARD", 
	"DECK_RULESET_RULE_SUBSET", 
	"DECK_RULESET_RULE",
	"DECK_RULESET", 
	"DECK_TEMPLATE", 
	"DRAFT_CONTENT",
	"EXTERNAL_URL",
	"FIXED_REWARD_ACTION",
	"FIXED_REWARD_MAP",
	"FIXED_REWARD", 
	"GAME_MODE",
	"GAME_SAVE_SUBKEY",
	"GLOBAL",
	"GUEST_HERO_SELECTION_RATIO",
	"GUEST_HERO",
	"HIDDEN_LICENSE",
	"KEYWORD_TEXT", 
	"LEAGUE_BG_PUBLIC_RATING_EQUIV",
	"LEAGUE_GAME_TYPE",
	"LEAGUE_RANK",
	"LEAGUE", 
	"LETTUCE_ABILITY_TIER",
	"LETTUCE_ABILITY",
	"LETTUCE_BOUNTY_FINAL_REWARDS", 
	"LETTUCE_BOUNTY_FINAL_RESPRESENTIVE_REWARDS", 
	"LETTUCE_BOUNTY_SET", 
	"LETTUCE_BOUNTY", 
	"LETTUCE_EQUIPMENT_MODIFIER_DATA",
	"LETTUCE_EQUIPMENT_TIER",
	"LETTUCE_EQUIPMENT",
	"LETTUCE_MAP_NODE_TYPE",
	"LETTUCE_MAP_NODE_TYPE_ANOMALY",
	"LETTUCE_MERCENARY_ABILITY", 
	"LETTUCE_MERCENARY_EQUIPMENT", 
	"LETTUCE_MERCENARY_LEVEL_STATS",
	"LETTUCE_MERCENARY_LEVEL", 
	"LETTUCE_MERCENARY_SPECIALIZATION",
	"LETTUCE_MERCENARY",
	"LETTUCE_TREASURE",
	"LETTUCE_TUTORIAL_VO", 
	"LOGIN_POPUP_SEQUENCE_POPUP",
	"LOGIN_POPUP_SEQUENCE",
	"LOGIN_REWARD",
	"MERC_TRIGGERED_EVENT", 
	"MERC_TRIGGERING_EVENT", 
	"MERCENARIES_RANDOM_REWARD", 
	"MERCENARIES_RANKED_SEASON_REWARD_RANK", 
	"MERCENARY_ALLOWED_TREASURE", 
	"MERCENARY_ART_VARIATION_PREMIUM", 
	"MERCENARY_ART_VARIATION",
	"MERCENARY_BUILDING", 
	"MERCENARY_VILLAGE_TRIGGER",
	"MERCENARY_VISITOR",
	"MINI_SET",
	"MODIFIED_LETTUCE_ABILITY_VALUE", 
	"MODIFIED_LETTUCE_ABILITY_CARD_TAG", 
	"MODULAR_BUNDLE_LAYOUT_NODE",
	"MODULAR_BUNDLE_LAYOUT",
	"MODULAR_BUNDLE",
	"MULTI_CLASS_GROUP", 
	"MYTHIC_ABILITY_SCALING_CARD_TAG", 
	"MYTHIC_EQUIPMENT_SCALING_CARD_TAG", 
	"MYTHIC_EQUIPMENT_SCALING_DESTINATION_CARD_TAG", 
	"NEXT_TIERS", 
	"POWER_DEFINITION", 
	"SCALING_TREASURE_CARD_TAG", 
	"PRODUCT_CLIENT_DATA", 
	"PRODUCT",
	"PVPDR_SEASON",
	"QUEST_DIALOG_ON_COMPLETE",
	"QUEST_DIALOG_ON_PROGRESS1", 
	"QUEST_DIALOG_ON_PROGRESS2", 
	"QUEST_DIALOG_ON_RECEIVED",
	"QUEST_DIALOG",
	"QUEST_MODIFIER", 
	"QUEST_POOL", 
	"QUEST",
	"REGION_OVERRIDES", 
	"REPEATABLE_TASK_LIST", 
	"REWARD_BAG", 
	"REWARD_CHEST_CONTENTS",
	"REWARD_CHEST",
	"REWARD_ITEM", 
	"REWARD_LIST", 
	"REWARD_TRACK_LEVEL", 
	"REWARD_TRACK", 
	"SCENARIO_GUEST_HEROES",
	"SCENARIO",
	"SCHEDULED_CHARACTER_DIALOG",
	"SCORE_LABEL",
	"SELLABLE_DECK", 
	"SHOP_TIER_PRODUCT_SALE",
	"SHOP_TIER",
	"SUBSET_CARD", 
	"SUBSET_RULE",
	"SUBSET",
	"TASK_LIST", 
	"TAVERN_BRAWL_TICKET",
	"TIER_PROPERTIES",
	"TRIGGER",
	"VISITOR_TASK_CHAIN",
	"VISITOR_TASK",
	"WING", 
	"XP_ON_PLACEMENT", 
	"XP_ON_PLACEMENT_GAME_TYPE_MULTIPLIER", 
	"XP_PER_GAME_TYPE", 
	"XP_PER_TIME_GAME_TYPE_MULTIPLIER", 
]

def main():
	p = ArgumentParser()
	p.add_argument("src")
	args = p.parse_args(sys.argv[1:])
	extract_ref_objects(args.src)


def extract_ref_objects(src):
	for root, dirs, files in os.walk(src):
		# if len(nodes_to_parse) == local_state["total_handled"]:
		# 	return
		for file_name in files:
			# if len(nodes_to_parse) == local_state["total_handled"]:
			# 	return
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			env = UnityPy.load(file_path)
			handle_asset(env)


def handle_asset(env):
	for path, obj in env.container.items():
		# if len(nodes_to_parse) == local_state["total_handled"]:
		# 	return

		if obj.serialized_type.nodes:
			# save decoded data
			try:
				tree = obj.read_typetree()
			except:
				print("could not read %s" % obj.type)
				continue

			if "m_Name" in tree and tree["m_Name"] is not "":
				if (tree["m_Name"] == tree["m_Name"].upper()) and tree["m_Name"] not in nodes_to_parse:
					print("considering %s" % tree["m_Name"])
				# Has some data, but not everything (eg cost is not there, neither is collectible attribute)
				if tree["m_Name"] in nodes_to_parse:
					# print("parsing %s" % tree["m_Name"])
					# print("path %s" % path)
					name = tree["m_Name"]
					currentLoc = ''
					for loc in locales:
						if loc.lower() in path.lower():
							currentLoc = loc
					locName = name + "-" + currentLoc

					local_state["total_handled"] = local_state["total_handled"] + 1
					try:
						# Only save the data if it has records
						tree["Records"]
					except:
						continue

					# print("\tprocessing")
					# Not sure why, but if you don't do this you end up with read errors. Maybe the tree needs to be
					# fully traversed first so that references are resolved or something?
					# output = yaml.dump(d)
					fp = os.path.join(f"ref/objects", f"{locName}.json")
					with open(fp, "wt", encoding = "utf8") as f:
						json.dump(tree, f, ensure_ascii = False, indent = 4)

					# Store the reference (enUS) without the loc suffix, so that we only explicitly support locs if we want to
					# print("is ref? %s, %s" % (currentLoc.lower(), currentLoc.lower() == "enus"))
					if currentLoc.lower() == "enus":
						fp = os.path.join(f"ref/objects", f"{name}.json")
						with open(fp, "wt", encoding = "utf8") as f:
							json.dump(tree, f, ensure_ascii = False, indent = 4)



if __name__ == "__main__":
	main()

