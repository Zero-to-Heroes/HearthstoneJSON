#!/usr/bin/env python
import json
import os
import sys
import unitypack
import yaml

from argparse import ArgumentParser
from PIL import Image, ImageOps
from unitypack.environment import UnityEnvironment
from unitypack.asset import Asset
from unitypack.object import ObjectPointer
from unitypack.utils import extract_audioclip_samples

guid_to_path = {}


def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+")
	p.add_argument("-s", "--strip", action="store_true", help="Strip extractable data")
	args = p.parse_args(sys.argv[1:])

	yaml.add_representer(Asset, asset_representer)
	yaml.add_representer(ObjectPointer, objectpointer_representer)

	for k, v in unitypack.engine.__dict__.items():
		if isinstance(v, type) and issubclass(v, unitypack.engine.object.Object):
			yaml.add_representer(v, unityobj_representer)

	audioClips = {}

	for file in args.files:
		if file.endswith(".assets"):
			with open(file, "rb") as f:
				asset = Asset.from_file(f)
				populate_guid_to_path(asset, audioClips)
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)

			for asset in bundle.assets:
				populate_guid_to_path(asset, audioClips)

	cards = extract_info(args.files)
	with open('./sound_effects.json', 'w') as resultFile:
		resultFile.write(json.dumps(cards))


def populate_guid_to_path(asset, audioClips):
	for id, obj in asset.objects.items():
		try:
			d = obj.read()

			for asset_info in d["m_assets"]:
				guid = asset_info["Guid"]
				path = asset_info["Path"]
				path = path.lower()
				if not path.startswith("final/"):
					path = "final/" + path
				if not path.startswith("final/assets"):
					print("not handling path %s" % path)
					continue
				guid_to_path[guid] = path
				audioClips[path] = asset_info
		except:
			continue


def extract_info(files):
	audioClips = {}
	cards = {}
	env = UnityEnvironment()

	for file in files:
		f = open(file, "rb")
		env.load(f)

	for bundle in env.bundles.values():
		for asset in bundle.assets:
			handle_asset(asset, audioClips, cards)

	for bundle in env.bundles.values():
		for asset in bundle.assets:
			handle_gameobject(asset, audioClips, cards)

	return cards


def handle_asset(asset, audioClips, cards):
	for obj in asset.objects.values():
		if obj.type == "AssetBundle":
			d = obj.read()

			for path, obj in d["m_Container"]:
				path = path.lower()
				asset = obj["asset"]
				if path == "assets/rad/rad_base.asset" or path == "assets/rad/rad_enus.asset":
					handle_rad(asset.resolve())
				if not path.startswith("final/"):
					path = "final/" + path
				if not path.startswith("final/assets"):
					print("not handling path %s" % path)
					continue
				audioClips[path] = asset


def handle_gameobject(asset, audioClips, cards):
	for obj in asset.objects.values():
		if obj.type == "GameObject":
			d = obj.read()
			cardid = d.name

			if cardid in ("CardDefTemplate", "HiddenCard"):
				# not a real card
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

			card = {}
			card["play"] = extract_sound_file_names(audioClips, carddef, "m_PlayEffectDef")
			card["attack"] = extract_sound_file_names(audioClips, carddef, "m_AttackEffectDef")
			card["death"] = extract_sound_file_names(audioClips, carddef, "m_DeathEffectDef")
			spellSounds = extract_spell_sounds(audioClips, carddef)
			for spellSound in spellSounds:
				card[spellSound] = [spellSound + ".ogg"]

			cards[cardid] = card


def extract_sound_file_names(audioClips, carddef, node):
	path = carddef[node]
	if not path:
		return []

	path = path["m_SoundSpellPaths"]

	result = []
	for playEffectPath in path:
		updatedPath = playEffectPath
		if ":" in updatedPath:
			guid = updatedPath.split(":")[1]
			if guid in guid_to_path:
				updatedPath = guid_to_path[guid]
		if updatedPath and len(updatedPath) > 1:
			if not updatedPath.startswith("final/"):
				updatedPath = "final/" + updatedPath
			try:
				audioClip = audioClips[updatedPath.lower()].resolve()
			except Exception as e:
				print("Could not resolve audio clip %s" % e)
				continue
			audioGameObject = audioClip.component[1]["component"].resolve()
			if audioGameObject["m_CardSoundData"]["m_AudioSource"] is not None:
				audioSource = audioGameObject["m_CardSoundData"]["m_AudioSource"].resolve()
				audioClipGuid = audioSource.game_object.resolve().component[2]["component"].resolve()["m_AudioClip"]
				audioFileName = audioClipGuid.split(":")[0].split(".")[0]
				if audioFileName and len(audioFileName) > 1:
					result.append(audioFileName + ".ogg")

	return result

def extract_spell_sounds(audioClips, carddef):
	otherPlayAudio = carddef["m_PlayEffectDef"]["m_SpellPath"]
	if otherPlayAudio and ":" in otherPlayAudio:
		guid = otherPlayAudio.split(":")[1]
		try:
			if guid in guid_to_path:
				playEffectPath = guid_to_path[guid]
				if not playEffectPath.startswith("final/"):
					playEffectPath = "final/" + playEffectPath
				cardAudios = []
				audioClip = audioClips[playEffectPath.lower()].resolve()
				findAudios(audioClip, cardAudios, 0, [])
				return cardAudios
		except:
			return []
	return []


def findAudios(audioClip, cardAudios, level, iteratedValues):
	if hasattr(audioClip, "component"):
		for index, elem in enumerate(audioClip.component):
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
		for elem in audioClip:
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


def add_to_audio(cardAudios, audioElement):
	trimmed = audioElement.split(".")[0]
	if len(trimmed) > 0 and trimmed not in cardAudios:
		cardAudios.append(trimmed)


def handle_rad_node(path, guids, names, tree, node):
	if len(node["folderName"]) > 0:
		if len(path) > 0:
			path = path + "/" + node["folderName"]
		else:
			path = node["folderName"]

	# print("handling rad node %s" % path)
	for leaf in node["leaves"]:
		guid = guids[leaf["guidIndex"]]["GUID"]
		if guid == "2506aa06cb6227c4b9ff287a0b41dc80":
			print("GOT IT!!!!!!!!")
		name = names[leaf["fileNameIndex"]]
		guid_to_path[guid] = path + "/" + name

	for child in node["children"]:
		handle_rad_node(path, guids, names, tree, tree[child])


def handle_rad(rad):
	print("Handling RAD")
	guids = rad["m_guids"]
	names = rad["m_filenames"]
	tree = rad["m_tree"]
	handle_rad_node("", guids, names, tree, tree[0])


def dump(obj, level):
  for attr in dir(obj):
    print("\t" * level, "obj.%s = %r" % (attr, getattr(obj, attr)))


def asset_representer(dumper, data):
	return dumper.represent_scalar("!asset", data.name)


def objectpointer_representer(dumper, data):
	return dumper.represent_sequence("!PPtr", [data.file_id, data.path_id])


def unityobj_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:%s" % (data.__class__.__name__), data._obj)


if __name__ == "__main__":
	main()
