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
	if pretty:
		kwargs = {"sort_keys": True, "indent": "\t", "separators": (",", ": ")}
	else:
		kwargs = {"separators": (",", ":")}
	with open(filename, "w", encoding="utf8") as f:
		json.dump(obj, f, ensure_ascii=False, **kwargs)


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

	return ret


def serialize_card(card):
	ret = {
		"id": card.id,
		"name": card.name,
		"flavor": card.flavortext,
		"text": card.description.replace("_", NBSP),
		"textInPlay": card.playtext,
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
		GameTag.CardTextInPlay: "textInPlay",
		GameTag.HOW_TO_EARN: "howToEarn",
		GameTag.HOW_TO_EARN_GOLDEN: "howToEarnGolden",
		GameTag.TARGETING_ARROW_TEXT: "targetingArrowText",
	}
	ret = []
	for card in cards:
		obj = serialize_card(card)
		for tag, key in tag_names.items():
			value = card._localized_tags[tag]
			if key == "text":
				for k, v in value.items():
					value[k] = v.replace("_", NBSP)
			if value:
				obj[key] = value
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

	for locale in Locale:
		if locale.unused:
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
	basedir = os.path.join(args.output_dir, "all")
	if not os.path.exists(basedir):
		os.makedirs(basedir)
	filename = os.path.join(basedir, "cards.json")
	export_all_locales_cards_to_file(cards, filename)
	filename = os.path.join(basedir, "cards.collectible.json")
	export_all_locales_cards_to_file(collectible_cards, filename)


if __name__ == "__main__":
	main()
