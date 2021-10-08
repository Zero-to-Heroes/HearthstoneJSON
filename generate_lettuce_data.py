#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import unitypack
import yaml
from unitypack.asset import Asset
from unitypack.object import ObjectPointer

NBSP = "\u00A0"

data = {
	"bountySets": [],
	"equipmentTiers": [],
	"mercenaryLevels": [],
}

def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+")
	p.add_argument("-s", "--strip", action="store_true", help="Strip extractable data")
	args = p.parse_args(sys.argv[1:])

	for k, v in unitypack.engine.__dict__.items():
		if isinstance(v, type) and issubclass(v, unitypack.engine.object.Object):
			yaml.add_representer(v, unityobj_representer)

	if args.strip:
		yaml.add_representer(unitypack.engine.mesh.Mesh, mesh_representer)
		yaml.add_representer(unitypack.engine.movie.MovieTexture, movietexture_representer)
		yaml.add_representer(unitypack.engine.text.Shader, shader_representer)
		yaml.add_representer(unitypack.engine.text.TextAsset, textasset_representer)
		yaml.add_representer(unitypack.engine.texture.Texture2D, texture2d_representer)

	build_data(args.files)
	with open('./ref/reference_cards.json', 'w') as resultFile:
		resultFile.write(json.dumps(data))


def build_data(files):
	for file in files:
		if file.endswith(".assets"):
			with open(file, "rb") as f:
				asset = Asset.from_file(f)
				handle_asset(asset)
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)
			for asset in bundle.assets:
				handle_asset(asset)


def handle_asset(asset):
	for id, obj in asset.objects.items():
		if obj.type == "AnimationClip":
			# There are issues reading animation clips, and we don't need them for cards
			continue

		try: 
			d = obj.read()
		except Exception as e:
			print("Could not read asset %s, %s, %s, %s" % (id, obj, asset, e))
			raise e

		if isinstance(d, dict):
			# print("is dict! %s: %s" % (id, d))
			if "m_Name" in d and d["m_Name"] is not "":
				print("considering %s" % d["m_Name"])
				if d["m_Name"] in ["LETTUCE_ABILITY"]:
					# This seems to be a simple listing of all lvl 1 abilities
					a = 1
					# output = yaml.dump(d)
					# print(output)
					# records = d["Records"]
					# handle_lettuce_abilities(records)
				if d["m_Name"] in ["LETTUCE_MERCENARY_SPECIALIZATION"]:
					# List of all mercs ability categories or races? There are things like orc, shadow, attack, etc.
					a = 1
				if d["m_Name"] in ["LETTUCE_MERCENARY_LEVEL_STATS"]:
					# The stats (atk / health) of all mercenaries, level by level
					a = 1
				if d["m_Name"] in ["LETTUCE_BOUNTY_SET"]:
					a = 1
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_lettuce_bounty_sets(records)
				if d["m_Name"] in ["LETTUCE_EQUIPMENT_TIER"]:
					a = 1
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_lettuce_equipment_tiers(records)
				if d["m_Name"] in ["LETTUCE_MERCENARY_LEVEL"]:
					a = 1
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_lettuce_mercenary_levels(records)
				elif d["m_Name"] in ["LETTUCE_BOUNTY_FINAL_REWARDS", "LETTUCE_MERCENARY", "LETTUCE_EQUIPMENT_MODIFIER_DATA", "LETTUCE_MERCENARY_ABILITY", "MODIFIED_LETTUCE_ABILITY_VALUE", "LETTUCE_BOUNTY", "LETTUCE_EQUIPMENT", "LETTUCE_ABILITY_TIER", ]:
					a = 1
					output = yaml.dump(d)
					print(output)

					

def handle_lettuce_mercenary_levels(records):
	for record in records:
		handle_lettuce_mercenary_level(record)


def handle_lettuce_mercenary_level(record):
	level = {
		"currentLevel": record["m_level"],
		"xpToNext": record["m_totalXpRequired"],
	}
	data["mercenaryLevels"].append(level)
					

def handle_lettuce_equipment_tiers(records):
	for record in records:
		handle_lettuce_equipment_tier(record)


def handle_lettuce_equipment_tier(record):
	equipment = {
		"equipmentId": record["m_lettuceEquipmentId"],
		"tier": record["m_tier"],
		"cardId": record["m_cardId"],
		"coinCraftCost": record["m_coinCraftCost"],
	}
	data["equipmentTiers"].append(equipment)


def handle_lettuce_bounty_sets(records):
	for record in records:
		handle_lettuce_bounty_set(record)


def handle_lettuce_bounty_set(record):
	bountySet = {}
	for k, v in record.items():
		if k == "m_ID":
			bountySet["dbfId"] = v
		elif k == "m_name" and len(v["m_locValues"]) > 0:
			bountySet["name"] = v["m_locValues"][0]
		elif k == "m_descriptionNormal" and len(v["m_locValues"]) > 0:
			bountySet["descriptionNormal"] = v["m_locValues"][0]
		elif k == "m_descriptionHeroic" and len(v["m_locValues"]) > 0:
			bountySet["descriptionHeroic"] = v["m_locValues"][0]
		elif k == "m_descriptionLegendary" and len(v["m_locValues"]) > 0:
			bountySet["descriptionLegendary"] = v["m_locValues"][0]
		elif k == "m_unlockPopupText" and len(v["m_locValues"]) > 0:
			bountySet["unlockText"] = v["m_locValues"][0]
		elif k == "m_sortOrder":
			bountySet["sortOrder"] = v
		elif k == "m_shortGuid":
			bountySet["id"] = v
		elif k == "m_isTutorial" and v == 1:
			bountySet["isTutorial"] = True
	data["bountySets"].append(bountySet)




def asset_representer(dumper, data):
	return dumper.represent_scalar("!asset", data.name)
yaml.add_representer(Asset, asset_representer)


def objectpointer_representer(dumper, data):
	return dumper.represent_sequence("!PPtr", [data.file_id, data.path_id])
yaml.add_representer(ObjectPointer, objectpointer_representer)


def unityobj_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:%s" % (data.__class__.__name__), data._obj)


def shader_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:Shader", {data.name: None})


def textasset_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:TextAsset", {data.name: None})


def texture2d_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:Texture2D", {data.name: None})


def mesh_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:Mesh", {data.name: None})


def movietexture_representer(dumper, data):
	obj = data._obj.copy()
	obj["m_MovieData"] = "<stripped>"
	return dumper.represent_mapping("!unitypack:stripped:MovieTexture", obj)


def dump(obj, level):
  for attr in dir(obj):
    print("\t" * level, "obj.%s = %r" % (attr, getattr(obj, attr)))

if __name__ == "__main__":
	main()
