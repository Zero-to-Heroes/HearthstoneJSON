#!/usr/bin/env python
import sys
from hearthstone.cardxml import load as load_cardxml


def card_diff(first, other):
	ret = {
		"entourage": (),
		"hero_power": (),
		"play_requirements": {},
		"tags": {},
		"text": {},
	}

	for tag, value in other.tags.items():
		old_value = first.tags.get(tag, None)
		if value != old_value:
			if not isinstance(tag, int) and tag.string_type:
				ret["text"][tag] = (old_value, value)
			else:
				ret["tags"][tag] = (old_value, value)

	for pr, value in other.requirements.items():
		old_value = first.requirements.get(pr, None)
		if value != old_value:
			ret["play_requirements"][pr] = (old_value, value)

	# Deleted tags
	for tag, old_value in first.tags.items():
		if tag not in other.tags:
			ret["tags"][tag] = (old_value, None)

	if first.hero_power != other.hero_power:
		ret["hero_power"] = (first.hero_power, other.hero_power)

	if first.entourage != other.entourage:
		added = sorted(k for k in other.entourage if k not in first.entourage)
		deleted = sorted(k for k in first.entourage if k not in other.entourage)
		ret["entourage"] = (added, deleted)

	return ret


def get_new_values(attr, first, other):
	def get_values(cards):
		ret = set()
		for card in cards:
			for value in getattr(card, attr):
				ret.add(value)
		return ret

	old, new = get_values(first.values()), get_values(other.values())
	return [k for k in new if k not in old]


def get_tags(cards):
	ret = set()
	for card in cards:
		for tag in card.tags:
			ret.add(tag)
	return ret


def print_enum_diff(key, before, after):
	if before is None:
		print("  - ADDED %s = %r" % (key, after))
	elif after is None:
		if not before or not after:
			return
		print("  - DELETED %s (was: %r)" % (key, before))
	else:
		print("  - CHANGED %s: %r -> %r" % (key, before, after))


def print_report(old_path, new_path):
	print("OLD: %s" % (old_path))
	print("NEW: %s\n" % (new_path))

	first, first_xml = load_cardxml(old_path)
	other, other_xml = load_cardxml(new_path)
	new_cards = {k: v for k, v in other.items() if k not in first}
	deleted_cards = {k: v for k, v in first.items() if k not in other}

	if new_cards:
		print("%i new cards:" % (len(new_cards)))
		for id, card in sorted(new_cards.items()):
			print("* %r (%s): %s, %s - %r" % (card.name, id, card.card_set, card.type, card.description))
		print()

	if deleted_cards:
		print("%i deleted cards:" % (len(deleted_cards)))
		for id, card in sorted(deleted_cards.items()):
			print("* %r (%s)" % (card.name, id))
		print()

	changed_cards = {}
	text_changes = {}
	# Find changed cards
	for id, card in first.items():
		if id in deleted_cards:
			# Skip over deleted cards
			continue
		diff = card_diff(card, other[id])
		if diff["text"]:
			text_changes[card] = diff.pop("text")
		if any(diff.values()):
			changed_cards[other[id]] = diff

	if text_changes:
		text_changes = sorted(text_changes.items(), key=lambda t: t[0].id)
		print("%i text changes" % (len(text_changes)))

		for card, diff in text_changes:
			print("* %s (%s)" % (card.name, card.id))
			for tag, value in diff.items():
				print_enum_diff(tag, *value)
		print()

	if changed_cards:
		changed_cards = sorted(changed_cards.items(), key=lambda t: t[0].id)
		print("%i changed cards:" % (len(changed_cards)))
		for card, diff in changed_cards:
			print("* %s (%s)" % (card.name, card.id))
			for tag, value in diff["tags"].items():
				print_enum_diff(tag, *value)

			for pr, value in diff["play_requirements"].items():
				print_enum_diff(pr, *value)

			if diff["hero_power"]:
				print("  - UPDATED HERO POWER: %r -> %r" % diff["hero_power"])

			if diff["entourage"]:
				added, removed = diff["entourage"]
				print("  - UPDATED ENTOURAGE:")
				if added:
					print("    * ADDED: %s" % (", ".join(repr(other.get(id, id)) for id in added)))
				if removed:
					print("    * REMOVED: %s" % (", ".join(repr(first.get(id, id)) for id in removed)))
		print()

	new_tags = get_new_values("tags", first, other)
	if new_tags:
		print("%i new GameTag:" % (len(new_tags)))
		print(", ".join(repr(tag) for tag in new_tags))
		print()

	new_reftags = get_new_values("referenced_tags", first, other)
	if new_reftags:
		print("%i new Referenced Tags:" % (len(new_reftags)))
		print(", ".join(repr(tag) for tag in new_reftags))
		print()

	new_playreqs = get_new_values("requirements", first, other)
	if new_playreqs:
		print("%i new PlayReq:" % (len(new_playreqs)))
		print(", ".join(repr(pr) for pr in new_playreqs))
		print()


def main():
	args = sys.argv[1:]
	if len(args) < 2:
		raise ValueError("Need at least two arguments")

	if len(args) == 2:
		print_report(args[0], args[1])
	else:
		for old, new in zip(args, args[1:]):
			print_report(old, new)


if __name__ == "__main__":
	main()
