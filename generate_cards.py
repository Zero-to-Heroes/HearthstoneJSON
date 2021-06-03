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

# Use it to flag the individual cards that should not be split
SPELLSTONES = [
	# Spellstones
	"LOOT_043",
	"LOOT_051",
	"LOOT_064",
	"LOOT_091",
	"LOOT_103",
	"LOOT_503",
	"LOOT_507",
	"LOOT_526d",
]

SCHEMES = [
	# Schemes
	"DAL_007",
	"DAL_008",
	"DAL_009",
	"DAL_010",
	"DAL_011",
	"DALA_726",
	# Others
	"DAL_357t",
	"DALA_BOSS_69p",
	"DALA_BOSS_69px",
	"ULDA_804t",
	"DALA_BOSS_07p2",
	"ULDA_302",
	"ULDA_BOSS_03p",
	"BT_481",
	"TB_BaconShop_Triples_01",
	"TB_BaconShop_HP_047t",
	"BT_737e",
	"BT_850e",
	"LOOT_526e",
	"Prologue_DemonicPortal",
	"DMF_109",
	"DMF_254t3",
	"DMF_254t4",
	"DMF_254t5",
	"DMF_254t7",
	"TB_BaconShop_HP_065",
	"BTA_BOSS_16t",
	"BTA_BOSS_16t2",
	"TB_BaconShop_HP_068e",
	"BTA_09e",
	"BTA_BOSS_06te",
	"TB_BaconShop_HP_074",
	"TB_BaconShop_HP_076",
	"BTA_BOSS_16se",
	"PVPDR_SCH_Warlockt5",
	"TB_BaconShop_HP_087",
	"TB_BaconShop_HP_101t2",
	"TB_BaconShop_HP_102",
	"TB_BBR3_BOSS_03p1",
	"PVPDR_YOP_DruidT1",
	# TODO: use these patterns to try and reduce the manual stuff:
	# - if @ followed by "left", "time", "turn"
	# "PVPDR_SCH_DemonHuntert2e1",
	# "Story_04_ExhaustedRecruit",
	# "TB_BaconShop_HP_104",
	# "Story_04_Infectione",
	# "TB_BaconShop_HP_106",
	# "PVPDR_YOP_DemonHuntert1e1",
	# "PVPDR_YOP_DemonHuntert2",
	# "PVPDR_YOP_PriestT2",
]

cards = {}
unhandledAttributes = set()

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

	build_cards(args.files)
	print("unhandled attributes %s" % unhandledAttributes)
	with open('./ref/reference_cards.json', 'w') as resultFile:
		resultFile.write(json.dumps(cards))


def build_cards(files):
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
				# print("considering %s" % d["m_Name"])
				# Has some data, but not everything (eg cost is not there, neither is collectible attribute)
				if d["m_Name"] == "CARD":
					# Not sure why, but if you don't do this you end up with read errors. Maybe the tree needs to be
					# fully traversed first so that references are resolved or something?
					# output = yaml.dump(d)
					records = d["Records"]
					handle_records(records)
				# Internal oading stuff?
				if d["m_Name"].startswith("carddef_"):
					a = 1
				# Only has the name and property hashes
				elif d["m_Name"] == "CardDef":
					# Do nothing
					a = 1
				elif d["m_Name"] == "cards_map":
					# This is a mapping between the card ID and its prefab. Might be useful at some point later?
					a = 1
				elif d["m_Name"] == "DECK_CARD":
					# Looks like this gives the topCard for each deck? Didn't look deeply into it
					a = 1
				elif d["m_Name"] in ["Card", "CardDbfAsset", "CardSetDbfAsset", "CardTagDbfAsset", "CardHeroDbfAsset", "DeckCardDbfAsset"]:
					# These are actually not really interesting, just keeping them here to see I have gone through them
					a = 1
				elif d["m_Name"] in ["tags_metadata"]:
					# not the tag names mappings, just some metadata about tags and tag groups
					a = 1
				elif d["m_Name"] in ["BOOSTER"]:
					# This is actually interesting, and has all the info about booster sets. Maybe use this to build the 
					# BoosterType enum?
					a = 1
				elif d["m_Name"] in ["BOARD"]:
					# Same here, we can probably use this to build the BOARD enum
					a = 1
				elif d["m_Name"] in ["SCENARIO"]:
					# Same here, can probably use it to build the Scenario enum instead of mapping everything by hand
					a = 1
				elif d["m_Name"] in ["CARD_CHANGE"]:
					# Looks like the list of cards that have undergone some kind of change (naturalize is there for instance)
					# but there is also a lot of non-usable data, so probably best to ignore it for now
					a = 1
					# output = yaml.dump(d)
					# print(output)
				elif d["m_Name"] in ["CARD_SET", "MINISET"]:
					a = 1
				elif d["m_Name"] in ["CARD_SET_TIMING"]:
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_card_sets(records)
				elif d["m_Name"] in ["XP_PER_GAME_TYPE"]:
					# Nothing interesting here, just a gameId <-> rewardTrackId mapping
					a = 1
				elif d["m_Name"] in ["CARD_TAG"]:
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_card_tags(records)


def handle_card_sets(records):
	for record in records:
		handle_card_set(record)

def handle_card_set(record):
	cardId = str(record["m_cardId"])
	existingCard = get_card(cardId)
	# I don't know why, but it looks like that the set ID can be assigned more than once
	# Maybe just keeping the first one is not good enough, I'll check
	if "setId" in existingCard and record["m_cardSetId"] == 4:
		return
	existingCard["setId"] = record["m_cardSetId"]
	cards[cardId] = existingCard


def handle_card_tags(records):
	for record in records:
		handle_card_tag(record)

def handle_card_tag(record):
	cardId = str(record["m_cardId"])
	existingCard = get_card(cardId)
	found = 0
	# Patch updates seem to simply re-add the tag, instead of overriding the previous 
	# value. So we need to keep only the latest one
	for index, item in enumerate(existingCard["tags"]):
		if item["tagId"] == record["m_tagId"]:
			item["tagValue"] = record["m_tagValue"]
			item["isReference"] = record["m_isReferenceTag"]
			item["isPowerKeyword"] = record["m_isPowerKeywordTag"]
			found = 1
			# if cardId == "30":
			# 	print("Updated: %s, %s, %s" % (item, record, existingCard))
			break
		
	if found == 0:
		tag = {
			"tagId": record["m_tagId"],
			"tagValue": record["m_tagValue"],
			"isReference": record["m_isReferenceTag"],
			"isPowerKeyword": record["m_isPowerKeywordTag"]
		}
		existingTags = existingCard["tags"]
		# print("handling tag %s, %s" % (tag, existingCard))
		existingTags.append(tag)
	# print("added tag %s, %s" % (existingCard, existingTags))
	cards[cardId] = existingCard


def handle_records(records):
	for record in records:
		handle_record(record)

def handle_record(record):
	# print("Handling new record")
	# print(yaml.dump(record))
	cardId = str(record["m_ID"])
	# print("Handling card %s" % cardId)
	# if cardId == "63264":
	# 	print("\tHandling new card")
	# 	print(yaml.dump(record))
	result = get_card(cardId)
	for k, v in record.items():
		if k == "m_ID":
			result["dbfId"] = v
		elif k == "m_noteMiniGuid":
			result["id"] = v
		elif k == "m_name" and len(v["m_locValues"]) > 0:
			result["name"] = v["m_locValues"][0]
		elif k == "m_textInHand":
			if len(v["m_locValues"]) > 0:
				localizedValue = v["m_locValues"][0]
				text, collection_text = clean_card_description(localizedValue, result["id"])
				result["text"] = text
				result["collectionText"] = collection_text
		elif k == "m_flavorText":
			if len(v["m_locValues"]) > 0:
				result["flavorText"] = v["m_locValues"][0]
		elif k == "m_artistName":
			result["artistName"] = v
		else:
			unhandledAttributes.add(k)
			# print("not handled attribute %s" % k)

		# try:
		# 	print("value %s" % v)
		# except:
		# 	print("issue getting %s" % k)
		
	# print("result %s" % result)
	cards[cardId] = result
	# if cardId == "63264":
	# 	print("\tHandled new card %s" % cards[cardId])


def get_card(cardId):
	if cardId in cards:
		return cards[cardId]
		
	card = {
		"dbfId": cardId,
		"tags": []
	}
	cards[cardId] = card
	return card


def clean_card_description(text, card_id):
	text = text.replace("_", NBSP)
	count = text.count("@")

	if not count:
		return text, ""

	if card_id in SPELLSTONES:
		return text.replace("@", ""), text.replace("@", "")
	if card_id in SCHEMES or card_id.startswith("BAR_763t"):
		return text.replace("@", "###"), text.replace("@", "###")


	# if card_id in MANUAL_REPLACES:
	# 	newText = text.replace("@", MANUAL_REPLACES[card_id])
	# 	print("Will replace manually %s, %s, %s" % (card_id, text, newText))
	# 	return newText, newText

	parts = text.split("@")
	if len(parts) == 2:
		text, collection_text = parts
		collectionTextForCheck = collection_text.strip().lower()
		if (collectionTextForCheck.startswith("damage") 
			or collectionTextForCheck.startswith("turn") 
			or collectionTextForCheck.startswith("time") 
			or collectionTextForCheck.startswith("left") 
			or "left!" in collectionTextForCheck
			or "turns)" in collectionTextForCheck
			or "improves" in collectionTextForCheck
			or "upgrades after each use" in collectionTextForCheck
			or text.endswith("$")
			or text.endswith("(")
			or text.endswith("+")):
			tmp = text + "###" + collection_text
			collection_text = text + "###" + collection_text
			text = tmp
		else:
			text = text.strip()
	elif len(parts) > 2:
		collection_text = parts[0]
		if collection_text.strip().endswith("+"):
			return text.replace("@", "###"), text.replace("@", "###")

	return text, collection_text


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
