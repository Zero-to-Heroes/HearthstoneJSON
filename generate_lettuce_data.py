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
	"mercenarySpecializations": [],
	"bountySets": [],
	"equipmentTiers": [],
	"equipmentModifiers": [],
	"mercenaryLevels": [],
	"bountyFinalRewards": [],
	"mercenaries": [],
	"bounties": [],
	"abilityTiers": [],
	"mercenaryAbilities": [],
	"mercenaryEquipments": [],
	"mercenaryArtVariations": [],
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
	with open('./ref/mercenaries_data.json', 'w') as resultFile:
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
				elif d["m_Name"] in ["LETTUCE_MERCENARY_SPECIALIZATION"]:
					a = 1
					# List of all mercs ability categories or races? There are things like orc, shadow, attack, etc.
					# Each specialization only links to one single mercenary, so maybe this could be used as a substitute 
					# for mercenaryId?
					records = d["Records"]
					handle_lettuce_mercenary_specializations(records)
				elif d["m_Name"] in ["LETTUCE_MERCENARY_LEVEL_STATS"]:
					# The stats (atk / health) of all mercenaries, level by level
					a = 1
				elif d["m_Name"] in ["LETTUCE_BOUNTY_SET"]:
					a = 1
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_lettuce_bounty_sets(records)
				elif d["m_Name"] in ["LETTUCE_EQUIPMENT_TIER"]:
					a = 1
					# Here is the mapping between equipment ID and card ID!
					records = d["Records"]
					handle_lettuce_equipment_tiers(records)
				elif d["m_Name"] in ["LETTUCE_MERCENARY_LEVEL"]:
					a = 1
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_lettuce_mercenary_levels(records)
				elif d["m_Name"] in ["LETTUCE_BOUNTY_FINAL_REWARDS"]:
					a = 1
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_lettuce_bounty_final_rewards(records)
				elif d["m_Name"] in ["LETTUCE_MERCENARY"]:
					a = 1
					# This seems to be a simple mapping between ID and merc name.
					# Doesn't look like there is any DBF id in there though?
					records = d["Records"]
					handle_lettuce_mercenaries(records)
				elif d["m_Name"] in ["LETTUCE_EQUIPMENT_MODIFIER_DATA"]:
					a = 1
					# This seems to be a simple mapping between ID and merc name.
					# Doesn't look like there is any DBF id in there though?
					records = d["Records"]
					handle_lettuce_equipment_modifier_datas(records)
				elif d["m_Name"] in ["LETTUCE_MERCENARY_ABILITY"]:
					a = 1
					# Mapping between abilityId, specializationId, and min merc level
					records = d["Records"]
					handle_lettuce_mercenary_abilities(records)
				elif d["m_Name"] in ["MODIFIED_LETTUCE_ABILITY_VALUE"]:
					# How each ability affects health, cooldown, speed, etc.
					# Might be interesting to add, but I still don't have a mapping
					# between an ability ID and a dbfCardId
					a = 1
				elif d["m_Name"] in ["LETTUCE_BOUNTY"]:
					a = 1
					records = d["Records"]
					handle_lettuce_bounties(records)
				elif d["m_Name"] in ["LETTUCE_EQUIPMENT"]:
					# List of equipments + name (somewhat, it is Sharpened Axe LETL_501 or LETL_265_01 - Swiftfeather Bow 1)
					a = 1
				elif d["m_Name"] in ["LETTUCE_MERCENARY_EQUIPMENT"]:
					a = 1
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_lettuce_mercenary_equipments(records)
				elif d["m_Name"] in ["LETTUCE_ABILITY_TIER"]:
					a = 1
					# Here is the mapping between ability ID and card ID!
					# No mapping between ability ID and merc ID though
					records = d["Records"]
					handle_lettuce_ability_tiers(records)
				elif d["m_Name"] in ["MERCENARY_ART_VARIATION"]:
					a = 1
					# Mapping between a merc ID and a card ID
					records = d["Records"]
					handle_lettuce_mercenary_art_variations(records)
				elif d["m_Name"] in ["MERCENARY_ART_VARIATION_PREMIUM"]:
					a = 1
					# No card ID here, so not sure what to do with the info
				elif d["m_Name"] in [""]:
					a = 1
					output = yaml.dump(d)
					print(output)


def handle_lettuce_mercenary_art_variations(records):
	for record in records:
		handle_lettuce_mercenary_art_variation(record)

def handle_lettuce_mercenary_art_variation(record):
	mercenaryArtVariation = {
		"id": record["m_ID"],
		"mercenaryId": record["m_lettuceMercenaryId"],
		"cardId": record["m_cardId"],
		"defaultVariation": record["m_defaultVariation"],
	}
	data["mercenaryArtVariations"].append(mercenaryArtVariation)


def handle_lettuce_mercenary_equipments(records):
	for record in records:
		handle_lettuce_mercenary_equipment(record)

def handle_lettuce_mercenary_equipment(record):
	mercenaryEquipment = {
		"id": record["m_ID"],
		"mercenaryId": record["m_lettuceMercenaryId"],
		"equipmentId": record["m_lettuceEquipmentId"],
	}
	data["mercenaryEquipments"].append(mercenaryEquipment)


def handle_lettuce_mercenary_abilities(records):
	for record in records:
		handle_lettuce_mercenary_ability(record)

def handle_lettuce_mercenary_ability(record):
	mercenaryAbility = {
		"id": record["m_ID"],
		"specializationId": record["m_lettuceMercenarySpecializationId"],
		"abilityId": record["m_lettuceAbilityId"],
		"mercenaryRequiredLevelId": record["m_lettuceMercenaryLevelIdRequiredId"],
	}
	data["mercenaryAbilities"].append(mercenaryAbility)


def handle_lettuce_ability_tiers(records):
	for record in records:
		handle_lettuce_ability_tier(record)

def handle_lettuce_ability_tier(record):
	abilityTier = {
		"id": record["m_ID"],
		"abilityId": record["m_lettuceAbilityId"],
		"tier": record["m_tier"],
		"cardId": record["m_cardId"],
		"coinCraftCost": record["m_coinCraftCost"],
	}
	data["abilityTiers"].append(abilityTier)


def handle_lettuce_mercenary_specializations(records):
	for record in records:
		handle_lettuce_mercenary_specialization(record)

def handle_lettuce_mercenary_specialization(record):
	spec = {
		"id": record["m_ID"],
		"mercenaryId": record["m_lettuceMercenaryId"],
		"name": record["m_name"]["m_locValues"][0] if len(record["m_name"]["m_locValues"]) > 0 else ""
	}
	data["mercenarySpecializations"].append(spec)


def handle_lettuce_bounties(records):
	for record in records:
		handle_lettuce_bounty(record)

def handle_lettuce_bounty(record):
	bounty = {
		"id": record["m_ID"],
		"name": record["m_noteDesc"],
		"level": record["m_bountyLevel"],
		"enabled": record["m_enabled"],
		"setId": record["m_bountySetId"],
		"difficultyMode": record["m_difficultyMode"],
		"heroic": record["m_heroic"],
		"finalBossCardId": record["m_finalBossCardId"],
		"sortOrder": record["m_sortOrder"],
		"requiredCompletedBountyId": record["m_requiredCompletedBountyId"]
	}
	data["bounties"].append(bounty)


def handle_lettuce_mercenaries(records):
	for record in records:
		handle_lettuce_mercenary(record)

def handle_lettuce_mercenary(record):
	mercenary = {
		"id": record["m_ID"],
		"name": record["m_noteDesc"]
	}
	data["mercenaries"].append(mercenary)


def handle_lettuce_bounty_final_rewards(records):
	for record in records:
		handle_lettuce_bounty_final_reward(record)

def handle_lettuce_bounty_final_reward(record):
	bountyReward = {
		"id": record["m_ID"],
		"bountyId": record["m_lettuceBountyId"],
		"rewardMercenaryId": record["m_rewardMercenaryId"]
	}
	data["bountyFinalRewards"].append(bountyReward)
					

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
		"id": record["m_ID"],
		"equipmentId": record["m_lettuceEquipmentId"],
		"tier": record["m_tier"],
		"cardId": record["m_cardId"],
		"coinCraftCost": record["m_coinCraftCost"],
	}
	data["equipmentTiers"].append(equipment)
	

def handle_lettuce_equipment_modifier_datas(records):
	for record in records:
		handle_lettuce_equipment_modifier_data(record)

def handle_lettuce_equipment_modifier_data(record):
	equipment = {
		"id": record["m_ID"],
		"tier": record["m_lettuceEquipmentTierId"],
		"attack": record["m_mercenaryAttackChange"],
		"health": record["m_mercenaryHealthChange"],
	}
	data["equipmentModifiers"].append(equipment)


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
