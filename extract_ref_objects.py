#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import UnityPy

local_state = {
	"total_handled": 0,
}
nodes_to_parse = ["ACHIEVEMENT", "ACHIEVEMENT_SECTION", "ACHIEVEMENT_SECTION_ITEM", "ACHIEVEMENT_SUBCATEGORY", "ACHIEVEMENT_CATEGORY", "BOARD", "CARD", "CARD_BACK", "CARD_SET_TIMING", "CARD_TAG", "LETTUCE_ABILITY_TIER", "LETTUCE_BOUNTY", "LETTUCE_BOUNTY_FINAL_REWARDS", "LETTUCE_BOUNTY_SET", "LETTUCE_EQUIPMENT_MODIFIER_DATA", "LETTUCE_EQUIPMENT_TIER", "LETTUCE_MERCENARY", "LETTUCE_MERCENARY_ABILITY", "LETTUCE_MERCENARY_EQUIPMENT", "LETTUCE_MERCENARY_LEVEL", "LETTUCE_MERCENARY_SPECIALIZATION", "MERCENARY_ART_VARIATION", "MERCENARY_ART_VARIATION_PREMIUM", "MERCENARY_VISITOR", "REWARD_ITEM", "VISITOR_TASK", "VISITOR_TASK_CHAIN", "SCENARIO", 'LETTUCE_MERCENARY_LEVEL_STATS']

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
