#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser
from PIL import Image, ImageOps
from unitypack.environment import UnityEnvironment


guid_to_path = {}

def main():
	p = ArgumentParser()
	p.add_argument("--outdir", nargs="?", default="")
	p.add_argument("--skip-existing", action="store_true")
	p.add_argument(
		"--only", type=str, nargs="?", help="Extract specific CardIDs (case-insensitive)"
	)
	p.add_argument("--traceback", action="store_true", help="Raise errors during conversion")
	p.add_argument("files", nargs="+")
	args = p.parse_args(sys.argv[1:])

	filter_ids = args.only.lower().split(",") if args.only else []

	cards = extract_info(args.files, filter_ids)
	# print("Found %d cards" % len(cards))
	# print(cards)
	with open('./sound_effects.json', 'w') as resultFile:
		resultFile.write(json.dumps(cards))


def extract_info(files, filter_ids):
	cards = {}
	audioClips = {}
	env = UnityEnvironment()

	for file in files:
		# print("Reading %r" % (file))
		f = open(file, "rb")
		env.load(f)

	for bundle in env.bundles.values():
		for asset in bundle.assets:
			print("Parsing %r" % (asset.name))
			handle_asset(asset, audioClips, cards, filter_ids)

	for bundle in env.bundles.values():
		for asset in bundle.assets:
			print("Handling %r" % (asset.name))
			handle_gameobject(asset, audioClips, cards, filter_ids)

	return cards


def handle_asset(asset, audioClips, cards, filter_ids):
	for obj in asset.objects.values():
		if obj.type == "AssetBundle":
			d = obj.read()

			for path, obj in d["m_Container"]:
				path = path.lower()
				asset = obj["asset"]
				if path == "assets/rad/rad_base.asset":
					handle_rad(asset.resolve())
				if not path.startswith("final/"):
					path = "final/" + path
				if not path.startswith("final/assets"):
					# print(path)
					continue
				audioClips[path] = asset

def handle_gameobject(asset, audioClips, cards, filter_ids):
	for obj in asset.objects.values():
		if obj.type == "GameObject":
			d = obj.read()

			if d.name == "rad_base":
				handle_rad(d)
				continue

			cardid = d.name

			if filter_ids and cardid.lower() not in filter_ids:
				continue
			if cardid in ("CardDefTemplate", "HiddenCard"):
				# not a real card
				# cards[cardid] = {"path": "", "tile": ""}
				continue
			if len(d.component) < 2:
				# Not a CardDef
				continue
			script = d.component[1]
			if isinstance(script, dict):  # Unity 5.6+
				carddef = script["component"].resolve()
			else:  # Unity <= 5.4
				carddef = script[1].resolve()

			if not isinstance(carddef, dict) or "m_PlayEffectDef" not in carddef:
				# Not a CardDef
				continue

			print("handling card: %s" % (cardid))
			# print("cardDef %s" % (carddef))
			card = {}
			card["play"] = extract_sound_file_names(audioClips, carddef, "m_PlayEffectDef")
			card["attack"] = extract_sound_file_names(audioClips, carddef, "m_AttackEffectDef")
			card["death"] = extract_sound_file_names(audioClips, carddef, "m_DeathEffectDef")
			spellSounds = extract_spell_sounds(audioClips, carddef)
			for spellSound in spellSounds:
				card[spellSound] = [spellSound + ".ogg"]

			# if cardid == "EX1_277":
			# 	print("Arcane missles: %s" % (card))
			# if cardid == "EX1_312":
			# 	print("Twisting Nether: %s" % (card))
			# if cardid == "EX1_407":
			# 	print("Brawl: %s" % (card))

			cards[cardid] = card
			# print(card)

def extract_spell_sounds(audioClips, carddef):
	otherPlayAudio = carddef["m_PlayEffectDef"]["m_SpellPath"]
	if otherPlayAudio and ":" in otherPlayAudio:
		guid = otherPlayAudio.split(":")[1]
		if guid in guid_to_path:
			playEffectPath = "final/" + guid_to_path[guid]
			# print("playEffectPath=%s" % (playEffectPath))
			cardAudios = []
			try:
				audioClip = audioClips[playEffectPath.lower()].resolve()
				findAudios(audioClip, cardAudios, 0, [])
			except:
				print("Could not find audio asset %r" % (playEffectPath.lower()))
			# print("card audios: %s" % cardAudios)
			return cardAudios
		# else:
		# 	print("WARN: Could not find %s in guid_to_path (path=%s)" % (guid, otherPlayAudio))
	# print("Could not extract guid from %s" % carddef)
	return []


def findAudios(audioClip, cardAudios, level, iteratedValues):
	if hasattr(audioClip, "component"):
		for index, elem in enumerate(audioClip.component):
			# print("\t" * level, "considering with component %s: %s" % (index, elem))
			try:
				resolved = elem.resolve()
				if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
					add_to_audio(cardAudios, resolve["m_AudioClip"])
				if elem.path_id not in iteratedValues:
					iteratedValues.append(elem.path_id)
					findAudios(resolved, cardAudios, level + 1, iteratedValues)
			except:
				findAudios(elem, cardAudios, level + 1, iteratedValues)
		return
	if isinstance(audioClip, dict):
		for index, (key, value) in enumerate(audioClip.items()):
			# if not isinstance(value, dict) or len(value.items()) < 3:
				# print("\t" * level, "considering %s: (%s, %s)" % (index, key, value))
			# else:
				# print("\t" * level, "considering %s: %s (dict)" % (index, key))
			if key == "m_AudioClip":
				add_to_audio(cardAudios, value)
			try:
				resolved = value.resolve()
				if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
					add_to_audio(cardAudios, resolved["m_AudioClip"])
				if value.path_id not in iteratedValues:
					iteratedValues.append(value.path_id)
					findAudios(resolved, cardAudios, level + 1, iteratedValues)
			except:
				findAudios(value, cardAudios, level + 1, iteratedValues)
		return
	if hasattr(audioClip, "m_AudioClip") and audioClip["m_AudioClip"] is not None:
		add_to_audio(cardAudios, audioClip["m_AudioClip"])
		return
	if isinstance(audioClip, list):
		# print("\t" * level, "Found list: %s" % (len(audioClip)))
		for elem in audioClip:
			# print("\t" * level, "considering list element: %s" % elem)
			try:
				resolved = elem.resolve()
				if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
					add_to_audio(cardAudios, audioClip["m_AudioClip"])
				if elem.path_id not in iteratedValues:
					iteratedValues.append(elem.path_id)
					findAudios(resolved, cardAudios, level + 1, iteratedValues)
			except:
				findAudios(elem, cardAudios, level + 1, iteratedValues)
		return
	if hasattr(audioClip, "_obj"):
		findAudios(audioClip._obj, cardAudios, level + 1, iteratedValues)
		return
	if type(audioClip) in (int, float, bool, str):
		return
	if audioClip is None:
		return
	try:
		resolved = elem.resolve()
		if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
			add_to_audio(cardAudios, resolved["m_AudioClip"])
		if elem.path_id not in iteratedValues:
			iteratedValues.append(elem.path_id)
			findAudios(resolved, cardAudios, level + 1, iteratedValues)
		return
	except:
		return
	# print("\t" * level, "unparsable %s" % (audioClip))
	dump(audioClip, level)

def add_to_audio(cardAudios, audioElement):
	trimmed = audioElement.split(".")[0]
	if len(trimmed) > 0 and trimmed not in cardAudios:
		cardAudios.append(trimmed)

def extract_sound_file_names(audioClips, carddef, node):
	path = carddef[node]
	if not path:
		return []

	path = path["m_SoundSpellPaths"]

	result = []
	for playEffectPath in path:
		if ":" in playEffectPath:
			guid = playEffectPath.split(":")[1]
			if guid in guid_to_path:
				playEffectPath = guid_to_path[guid]
			# else:
				# print("WARN: Could not find %s in guid_to_path (path=%s)" % (guid, playEffectPath))
		if playEffectPath and len(playEffectPath) > 1:
			playEffectPath = "final/" + playEffectPath
			# print()
			# print("Handling %s" % (playEffectPath))
			try:
				audioClip = audioClips[playEffectPath.lower()].resolve()
				audioGameObject = audioClip.component[1]["component"].resolve()
				# dump(audioGameObject)
				# print("m_CardSoundData %s" % (audioGameObject["m_CardSoundData"]))
				# print("m_AudioSource %s" % (audioGameObject["m_CardSoundData"]["m_AudioSource"]))
				# dump(audioGameObject["m_CardSoundData"]["m_AudioSource"])
				if audioGameObject["m_CardSoundData"]["m_AudioSource"] is not None:
					audioSource = audioGameObject["m_CardSoundData"]["m_AudioSource"].resolve()
					audioClipGuid = audioSource.game_object.resolve().component[2]["component"].resolve()["m_AudioClip"]
					audioFileName = audioClipGuid.split(":")[0].split(".")[0]
					if audioFileName and len(audioFileName) > 1:
						result.append(audioFileName + ".ogg")
			except:
				print("Could not find audio asset to build component sound %r" % (playEffectPath.lower()))

	return result
	test = guid_to_path


def handle_rad_node(path, guids, names, tree, node):
	if len(node["folderName"]) > 0:
		if len(path) > 0:
			path = path + "/" + node["folderName"]
		else:
			path = node["folderName"]

	for leaf in node["leaves"]:
		guid = guids[leaf["guidIndex"]]
		name = names[leaf["fileNameIndex"]]
		guid_to_path[guid] = path + "/" + name

	for child in node["children"]:
		handle_rad_node(path, guids, names, tree, tree[child])


def handle_rad(rad):
	# print("Handling RAD")
	guids = rad["m_guids"]
	names = rad["m_filenames"]
	tree = rad["m_tree"]
	handle_rad_node("", guids, names, tree, tree[0])


# def dump(obj, level):
  # for attr in dir(obj):
    # print("\t" * level, "obj.%s = %r" % (attr, getattr(obj, attr)))

if __name__ == "__main__":
	main()
