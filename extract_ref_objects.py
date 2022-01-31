#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import UnityPy

local_state = {
	"total_handled": 0,
}
nodes_to_parse = ["MERC_TRIGGERED_EVENT", "MERCENARIES_RANKED_SEASON_REWARD_RANK", "REGION_OVERRIDES", "MERCENARY_BUILDING", "CARD_CHANGE", "BOOSTER_CARD_SET", "TASK_LIST", "CARD_TAG", "REWARD_BAG", "LOGIN_POPUP_SEQUENCE_POPUP", "BUILDING_TIER", "REWARD_LIST", "BATTLEGROUNDS_SEASON", "MERCENARIES_RANDOM_REWARD", "CHARACTER_DIALOG_ITEMS", "ADVENTURE_GUEST_HEROES", "QUEST_MODIFIER", "DECK_TEMPLATE", "SELLABLE_DECK", "DECK_RULESET_RULE_SUBSET", "CARD_DISCOVER_STRING", "QUEST_DIALOG_ON_PROGRESS1", "SUBSET_CARD", "MERCENARY_ART_VARIATION_PREMIUM", "LETTUCE_BOUNTY_FINAL_REWARDS", "CARD_HERO", "ACHIEVEMENT_SECTION_ITEM", "CHARACTER_DIALOG", "XP_PER_GAME_TYPE", "LETTUCE_MERCENARY_ABILITY", "MERC_TRIGGERING_EVENT", "NEXT_TIERS", "QUEST_POOL", "MODIFIED_LETTUCE_ABILITY_VALUE", "WING", "MULTI_CLASS_GROUP", "ACCOUNT_LICENSE", "BOOSTER", "BANNER", "REPEATABLE_TASK_LIST", "DECK_CARD", "DECK_RULESET", "ACHIEVE_CONDITION", "REWARD_TRACK_LEVEL", "LETTUCE_MERCENARY_LEVEL", "BATTLEGROUNDS_HERO_SKIN", "KEYWORD_TEXT", "ACHIEVE_REGION_DATA", "ACHIEVEMENT_SUBCATEGORY", "CARD_SET", "LEAGUE", "FIXED_REWARD", "LETTUCE_TUTORIAL_VO", "PRODUCT_CLIENT_DATA", "REWARD_ITEM", "LETTUCE_BOUNTY", "CLASS", "COIN", "REWARD_TRACK", "QUEST_DIALOG_ON_PROGRESS2", "LETTUCE_MERCENARY_EQUIPMENT", "FIXED_REWARD_ACTION", "GAME_SAVE_SUBKEY", "CLASS_EXCLUSIONS", "CARD_PLAYER_DECK_OVERRIDE", "CARD", "DECK_RULESET_RULE", "ACHIEVE", "LETTUCE_MERCENARY_LEVEL_STATS", "EXTERNAL_URL", "PVPDR_SEASON", "GUEST_HERO_SELECTION_RATIO", "LEAGUE_GAME_TYPE", "DRAFT_CONTENT", "VISITOR_TASK_CHAIN", "TAVERN_BRAWL_TICKET", "LETTUCE_EQUIPMENT", "TIER_PROPERTIES", "SUBSET_RULE", "GUEST_HERO", "LEAGUE_BG_PUBLIC_RATING_EQUIV", "LETTUCE_EQUIPMENT_TIER", "MERCENARY_ART_VARIATION", "SCORE_LABEL", "QUEST", "LETTUCE_ABILITY_TIER", "ADVENTURE_MODE", "HIDDEN_LICENSE", "ADVENTURE_DATA", "MODULAR_BUNDLE_LAYOUT_NODE", "FIXED_REWARD_MAP", "CARD_SET_TIMING", "CREDITS_YEAR", "ADVENTURE_LOADOUT_TREASURES", "SHOP_TIER", "ADVENTURE_MISSION", "QUEST_DIALOG_ON_COMPLETE", "MODULAR_BUNDLE_LAYOUT", "QUEST_DIALOG_ON_RECEIVED", "MERCENARY_VISITOR", "TRIGGER", "LETTUCE_MERCENARY_SPECIALIZATION", "CARD_ADDITONAL_SEARCH_TERMS", "VISITOR_TASK", "MODULAR_BUNDLE", "LETTUCE_EQUIPMENT_MODIFIER_DATA", "REWARD_CHEST", "ACHIEVEMENT", "BOARD", "SCENARIO_GUEST_HEROES", "ACHIEVEMENT_CATEGORY", "CLIENT_STRING", "ADVENTURE_HERO_POWER", "PRODUCT", "CARD_BACK", "BATTLEGROUNDS_BOARD_SKIN", "GLOBAL", "ADVENTURE", "LETTUCE_MAP_NODE_TYPE", "SCENARIO", "BONUS_BOUNTY_DROP_CHANCE", "LETTUCE_ABILITY", "LOGIN_POPUP_SEQUENCE", "CARD_EQUIPMENT_ALT_TEXT", "REWARD_CHEST_CONTENTS", "ADVENTURE_DECK", "SHOP_TIER_PRODUCT_SALE", "MINI_SET", "SUBSET", "QUEST_DIALOG", "LEAGUE_RANK", "CARD_SET_SPELL_OVERRIDE", "LOGIN_REWARD", "LETTUCE_MERCENARY", "BATTLEGROUNDS_GUIDE_SKIN", "SCHEDULED_CHARACTER_DIALOG", "ACHIEVEMENT_SECTION"]

def main():
	p = ArgumentParser()
	p.add_argument("src")
	args = p.parse_args(sys.argv[1:])
	extract_ref_objects(args.src)


def extract_ref_objects(src):
	for root, dirs, files in os.walk(src):
		if len(nodes_to_parse) == local_state["total_handled"]:
			return
		for file_name in files:
			if len(nodes_to_parse) == local_state["total_handled"]:
				return
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			env = UnityPy.load(file_path)
			handle_asset(env)


def handle_asset(env):
	for obj in env.objects:
		if len(nodes_to_parse) == local_state["total_handled"]:
			return

		if obj.serialized_type.nodes:
			# save decoded data
			try:
				tree = obj.read_typetree()
			except:
				print("could not read %s" % obj.type)
				continue

			if "m_Name" in tree and tree["m_Name"] is not "":
				if (tree["m_Name"] == tree["m_Name"].upper()):
					print("considering %s" % tree["m_Name"])
				# Has some data, but not everything (eg cost is not there, neither is collectible attribute)
				if tree["m_Name"] in nodes_to_parse:
					local_state["total_handled"] = local_state["total_handled"] + 1
					try:
						# Only save the data if it has records
						tree["Records"]
					except:
						continue

					print("\tprocessing")
					# Not sure why, but if you don't do this you end up with read errors. Maybe the tree needs to be
					# fully traversed first so that references are resolved or something?
					# output = yaml.dump(d)
					name = tree["m_Name"]
					fp = os.path.join(f"ref/objects", f"{name}.json")
					with open(fp, "wt", encoding = "utf8") as f:
						json.dump(tree, f, ensure_ascii = False, indent = 4)


if __name__ == "__main__":
	main()
