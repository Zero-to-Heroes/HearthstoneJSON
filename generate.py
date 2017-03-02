#!/usr/bin/env python
import os
import json
import sys
from argparse import ArgumentParser
from enum import IntEnum
from hearthstone.dbf import Dbf
from hearthstone.cardxml import load
from hearthstone.enums import CardType, Faction, GameTag, Locale


NBSP = "\u00A0"
MECHANICS_TAGS = [
	GameTag.ADJACENT_BUFF,
	GameTag.AI_MUST_PLAY,
	GameTag.AURA,
	GameTag.BATTLECRY,
	GameTag.CHARGE,
	GameTag.CHOOSE_ONE,
	GameTag.COMBO,
	GameTag.COUNTER,
	GameTag.DEATHRATTLE,
	GameTag.DISCOVER,
	GameTag.DIVINE_SHIELD,
	GameTag.ENRAGED,
	GameTag.EVIL_GLOW,
	GameTag.FORGETFUL,
	GameTag.FREEZE,
	GameTag.INSPIRE,
	GameTag.IMMUNE,
	GameTag.JADE_GOLEM,
	GameTag.MORPH,
	GameTag.POISONOUS,
	GameTag.RITUAL,
	GameTag.SECRET,
	GameTag.SILENCE,
	GameTag.STEALTH,
	GameTag.TAG_ONE_TURN_EFFECT,
	GameTag.TAUNT,
	GameTag.TOPDECK,
	GameTag.WINDFURY,
	GameTag.ImmuneToSpellpower,
	GameTag.InvisibleDeathrattle,
	GameTag.CANT_ATTACK,
	GameTag.CANT_BE_TARGETED_BY_ABILITIES,
	GameTag.CANT_BE_TARGETED_BY_HERO_POWERS,
]


def json_dump(obj, filename, pretty=False):
	print("Writing to %r" % (filename))
	kwargs = {
		"ensure_ascii": False,
		"separators": (",", ":"),
		"sort_keys": True,
	}
	if pretty:
		kwargs["indent"] = "\t"
		kwargs["separators"] = (",", ": ")

	with open(filename, "w", encoding="utf8") as f:
		json.dump(obj, f, **kwargs)


def show_field(card, k, v):
	if k == "cost" and card.type not in (CardType.ENCHANTMENT, CardType.HERO):
		return True
	if k == "faction" and v == Faction.NEUTRAL:
		return False
	if k == "attack" and card.type in (CardType.MINION, CardType.WEAPON):
		return True
	if k == "health" and card.type in (CardType.MINION, CardType.HERO):
		return True
	if k == "durability" and card.type == CardType.WEAPON:
		return True
	return bool(v)


def get_mechanics(card):
	ret = []
	for tag in MECHANICS_TAGS:
		value = card.tags.get(tag, 0)
		if value:
			ret.append(tag.name)

	# AUTOATTACK is only a referenced mechanic. Kinda weird.
	if card.referenced_tags.get(GameTag.AUTOATTACK):
		ret.append(GameTag.AUTOATTACK.name)

	# Do the same for JADE_GOLEM
	if card.referenced_tags.get(GameTag.JADE_GOLEM):
		ret.append(GameTag.JADE_GOLEM.name)

	return ret


def clean_card_description(text):
	text = text.replace("_", NBSP)

	if "@" in text:
		text, collection_text = text.split("@")
		text = text.strip()
		collection_text = collection_text.strip()
	else:
		collection_text = ""

	return text, collection_text


def serialize_card(card):
	text, collection_text = clean_card_description(card.description)

	ret = {
		"id": card.id,
		"dbfId": card.dbf_id,
		"name": card.name,
		"flavor": card.flavortext,
		"text": text,
		"collectionText": collection_text,
		"howToEarn": card.how_to_earn,
		"howToEarnGolden": card.how_to_earn_golden,
		"targetingArrowText": card.targeting_arrow_text,
		"artist": card.artist,
		"faction": card.faction,
		"playerClass": card.card_class,
		"race": card.race,
		"rarity": card.rarity,
		"set": card.card_set,
		"type": card.type,
		"collectible": card.collectible,
		"elite": card.elite,
		"attack": card.atk,
		"cost": card.cost,
		"durability": card.durability,
		"health": card.health,
		"overload": card.overload,
		"spellDamage": card.spell_damage,
	}
	ret = {k: v for k, v in ret.items() if show_field(card, k, v)}

	for k, v in ret.items():
		if isinstance(v, IntEnum):
			ret[k] = v.name

	mechanics = get_mechanics(card)
	if mechanics:
		ret["mechanics"] = mechanics

	if card.entourage:
		ret["entourage"] = card.entourage

	if card.multiple_classes:
		ret["classes"] = [c.name for c in card.classes]

	if card.multi_class_group:
		ret["multiClassGroup"] = card.multi_class_group.name

	if card.requirements:
		ret["playRequirements"] = {k.name: v for k, v in card.requirements.items()}

	if card.craftable:
		ret["dust"] = card.crafting_costs + card.disenchant_costs

	return ret


def export_cards_to_file(cards, filename, locale):
	ret = []
	for card in cards:
		card.locale = locale
		ret.append(serialize_card(card))

	json_dump(ret, filename)


def export_all_locales_cards_to_file(cards, filename):
	tag_names = {
		GameTag.CARDNAME: "name",
		GameTag.FLAVORTEXT: "flavor",
		GameTag.CARDTEXT_INHAND: "text",
		GameTag.HOW_TO_EARN: "howToEarn",
		GameTag.HOW_TO_EARN_GOLDEN: "howToEarnGolden",
		GameTag.TARGETING_ARROW_TEXT: "targetingArrowText",
	}
	ret = []

	for card in cards:
		obj = serialize_card(card)
		obj["collectionText"] = {}
		for tag, key in tag_names.items():
			value = card.strings.get(tag, {})
			if key == "text":
				for locale, localized_value in value.items():
					text, collection_text = clean_card_description(localized_value)
					value[locale] = text
					if collection_text:
						obj["collectionText"][locale] = collection_text
			if value:
				obj[key] = value

		if not obj["collectionText"]:
			del obj["collectionText"]

		ret.append(obj)

	json_dump(ret, filename)


def write_cardbacks(dbf, filename, locale):
	ret = []

	for record in dbf.records:
		name = record.get("NAME") or {}
		description = record.get("DESCRIPTION") or {}
		source_description = record.get("SOURCE_DESCRIPTION") or {}
		ret.append({
			"id": record["ID"],
			"note_desc": record["NOTE_DESC"],
			"source": record["SOURCE"],
			"enabled": record["ENABLED"],
			"name": name.get(locale.name, ""),
			"prefab_name": record.get("PREFAB_NAME", ""),
			"description": description.get(locale.name, ""),
			"source_description": source_description.get(locale.name, ""),
		})

	json_dump(ret, filename)


def main():
	parser = ArgumentParser()
	parser.add_argument(
		"-o", "--output-dir",
		type=str,
		dest="output_dir",
		default="out",
		help="Output directory"
	)
	parser.add_argument(
		"-i", "--input-dir",
		type=str,
		dest="input_dir",
		default="hsdata",
		help="Input hsdata directory"
	)
	parser.add_argument("--locale", type=str, nargs="*", help="Only generate one locale")
	args = parser.parse_args(sys.argv[1:])

	db, xml = load(os.path.join(args.input_dir, "CardDefs.xml"))
	dbf_path = os.path.join(args.input_dir, "DBF", "CARD_BACK.xml")
	if not os.path.exists(dbf_path):
		print("Skipping card back generation (%s does not exist)" % (dbf_path))
		dbf = None
	else:
		dbf = Dbf.load(dbf_path)

	cards = db.values()
	collectible_cards = [card for card in cards if card.collectible]

	filter_locales = [loc.lower() for loc in args.locale or []]

	for locale in Locale:
		if locale.unused:
			continue

		if filter_locales and locale.name.lower() not in filter_locales:
			continue

		basedir = os.path.join(args.output_dir, locale.name)
		if not os.path.exists(basedir):
			os.makedirs(basedir)

		filename = os.path.join(basedir, "cards.json")
		export_cards_to_file(cards, filename, locale.name)

		filename = os.path.join(basedir, "cards.collectible.json")
		export_cards_to_file(collectible_cards, filename, locale.name)

		if dbf is not None:
			filename = os.path.join(basedir, "cardbacks.json")
			write_cardbacks(dbf, filename, locale)

	# Generate merged locales
	if "all" in filter_locales or not filter_locales:
		basedir = os.path.join(args.output_dir, "all")
		if not os.path.exists(basedir):
			os.makedirs(basedir)
		filename = os.path.join(basedir, "cards.json")
		export_all_locales_cards_to_file(cards, filename)
		filename = os.path.join(basedir, "cards.collectible.json")
		export_all_locales_cards_to_file(collectible_cards, filename)


if __name__ == "__main__":
	main()
