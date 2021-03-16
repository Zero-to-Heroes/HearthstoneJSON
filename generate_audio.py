#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import unitypack
from PIL import Image, ImageOps
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment
from unitypack.object import ObjectPointer
from unitypack.utils import extract_audioclip_samples

guid_to_path = {}


def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+")
	p.add_argument("-s", "--strip", action="store_true", help="Strip extractable data")
	p.add_argument("--as-asset", action="store_true", help="Force open files as Asset format")
	args = p.parse_args(sys.argv[1:])

	audioClips = {}

	for file in args.files:
		# print("\nhandling file %s" % file)
		if args.as_asset or file.endswith(".assets"):
			# print("handling asset %s" % file)
			with open(file, "rb") as f:
				# print("doing it %s" % file)
				asset = Asset.from_file(f)
				populate_guid_to_path(asset, audioClips)
			continue

		with open(file, "rb") as f:
			# print("handling bundle %s" % file)
			bundle = unitypack.load(f)

			for asset in bundle.assets:
				# print("handling bundle asset %s" % asset)
				populate_guid_to_path(asset, audioClips)

	cards = extract_info(args.files)
	with open('./sound_effects.json', 'w') as resultFile:
		resultFile.write(json.dumps(cards))


def populate_guid_to_path(asset, audioClips):
	for id, obj in asset.objects.items():
		try:
			d = obj.read()
			# print("m_assets %s " % d)

			for asset_info in d["m_assets"]:
				guid = asset_info["Guid"]
				# print("print %s" % guid)
				path = asset_info["Path"]
				# print("path %s" % path)
				path = path.lower()
				# print("path lower %s" % path)
				if not path.startswith("final/"):
					path = "final/" + path
				if not path.startswith("final/assets"):
					# print("not handling path (%s : %s)" % (path, guid))
					continue
				# print("handling guid in populate_guid_to_path %s : %s" % (guid, path))
				# if guid == '4d4020cf2e9fe0b47bd47e669a5a7265':
				# 	print("handling 4d4020cf2e9fe0b47bd47e669a5a7265 in populate_guid_to_path %s" % (path))
				# if path == "Assets/Game/Cards/021 Gilneas/GILA_612/Death.prefab":
				# 	print("handling path in populate_guid_to_path %s" % (path))
				# if "GILA_612" in path:
				# 	print("handling GILA_612 in populate_guid_to_path %s, %s" % (guid, path))
				guid_to_path[guid] = path
				audioClips[path] = asset_info
		except Exception as e:
			# print("could not populate guid %s" % e)
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
				finalPath = path.lower()
				asset = obj["asset"]
				if finalPath == "assets/rad/rad_base.asset" or finalPath == "assets/rad/rad_enus.asset":
					handle_rad(asset.resolve())
				if not finalPath.startswith("final/"):
					finalPath = "final/" + finalPath
				# if path == "Assets/Game/Cards/021 Gilneas/GILA_612/Death.prefab":
				# 	print("handling path in handle_asset %s" % (path))
				# if "GILA_612" in path:
				# 	print("handling GILA_612 in handle_asset %s" % (path))
				# if "4d4020cf2e9fe0b47bd47e669a5a7265" in finalPath:
				# 	print("handling 4d4020cf2e9fe0b47bd47e669a5a7265 in handle_asset %s, %s" % (path, asset))
				audioClips[finalPath] = asset
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

			# if cardid != "CS2_029": # Fireball
			# 	continue

			# dump(carddef, 1)
			# print("Handling card %s " % cardid)
			card = {}
			playSounds = extract_sound_file_names(audioClips, carddef, "m_PlayEffectDef")
			if len(playSounds) > 0:
				card["BASIC_play"] = playSounds

			attackSounds = extract_sound_file_names(audioClips, carddef, "m_AttackEffectDef")
			if len(attackSounds) > 0:
				card["BASIC_attack"] = attackSounds

			deathSounds = extract_sound_file_names(audioClips, carddef, "m_DeathEffectDef")
			if len(deathSounds) > 0:
				card["BASIC_death"] = deathSounds

			spellSounds = extract_spell_sounds(audioClips, carddef)
			for spellSound in spellSounds:
				card["SPELL_" + spellSound] = [spellSound + ".ogg"]
				
			emoteSounds = extract_emote_sounds(audioClips, carddef)
			# print("emoteSounds %s" % emoteSounds)
			for emoteSound in emoteSounds:
				card[emoteSound["key"]] = [emoteSound["value"]]

			cards[cardid] = card


def extract_sound_file_names(audioClips, carddef, node):
	path = carddef[node]
	if not path:
		return []

	path = path["m_SoundSpellPaths"]

	result = []
	guid = ''
	for playEffectPath in path:
		# print("playEffectPath %s, %s" % (playEffectPath, path))
		updatedPath = playEffectPath
		if ":" in updatedPath:
			guid = updatedPath.split(":")[1]
			# print("guid %s" % (guid))
			if guid in guid_to_path:
				updatedPath = guid_to_path[guid]
				# print("updatedPath %s" % (updatedPath))
		if updatedPath and len(updatedPath) > 1:
			if not updatedPath.startswith("final/"):
				updatedPath = "final/" + updatedPath
			try:
				audioClip = audioClips[updatedPath.lower()].resolve()
			except Exception as e:
				if guid == '4d4020cf2e9fe0b47bd47e669a5a7265':
					print("Could not resolve audio clip (%s : %s : %s : %s)" % (e, updatedPath, guid, path))
				try :
					hop = audioClips[guid]
					# print("hop %s" % hop)
					audioClip = audioClips[guid].resolve()
				except Exception as f:
					if guid == '4d4020cf2e9fe0b47bd47e669a5a7265':
						print("Could not resolve audio clip from retry (%s)" % (f))
					# print("%s %s %s %s" % "e")
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
		# try:
		# print("\t guid_to_path %s" % (guid))
		if guid in guid_to_path:
			playEffectPath = guid_to_path[guid]
			# print("\t playEffectPath %s, %s" % (playEffectPath, guid))
			if not playEffectPath.startswith("final/"):
				playEffectPath = "final/" + playEffectPath
			cardAudios = []
			# print("\t sound %s" % playEffectPath)
			try:
				# print("\t\t will process %s" % updatedPath)
				audioClip = audioClips[playEffectPath.lower()].resolve()
			except Exception as e:
				try :
					# print("\t\t\t could not process %s, %s" % (updatedPath, e))
					audioClip = audioClips[guid].resolve()
				except Exception as f:
					# print("\t\t\t\t could not process at all %s, %s" % (updatedPath, f))
					return []
			findAudios(audioClip, cardAudios, 0, [])
			return cardAudios
		# except Exception as e:
		# 	print("Error %s" % e)
		# 	return []
	return []


def extract_emote_sounds(audioClips, carddef):
	sounds = []
	emoteSounds = carddef["m_EmoteDefs"]
	# print("emoteSounds %s" % emoteSounds)
	for emoteSound in emoteSounds:
		# print("\t emoteSound %s" % emoteSound)
		updatedPath = emoteSound["m_emoteSoundSpellPath"]
		# print("\t updatedPath %s" % updatedPath)
		soundInfo = extract_emote_sound(audioClips, updatedPath)
		# print("\t sound %s" % soundInfo)
		if len(soundInfo) > 0:
			sound = {}
			sound["key"] = emoteSound["m_emoteGameStringKey"]
			sound["value"] = soundInfo
			# print("adding sound %s" % sound)
			sounds.append(sound)
	# print("sounds %s" % sounds)
	return sounds


def extract_emote_sound(audioClips, updatedPath):
	guid = ''
	if ":" in updatedPath:
		guid = updatedPath.split(":")[1]
		# print("\t\t guid %s" % (guid))
		if guid in guid_to_path:
			updatedPath = guid_to_path[guid]
			# print("\t\t updatedPath %s" % (updatedPath))
	if updatedPath and len(updatedPath) > 1:
		if not updatedPath.startswith("final/"):
			updatedPath = "final/" + updatedPath
		try:
			# print("\t\t will process %s" % updatedPath)
			audioClip = audioClips[updatedPath.lower()].resolve()
		except Exception as e:
			try :
				# print("\t\t\t could not process %s, %s" % (updatedPath, e))
				audioClip = audioClips[guid].resolve()
			except Exception as f:
				# print("\t\t\t\t could not process at all %s, %s" % (updatedPath, f))
				return ''
		# print("\t\t audioclip component %s: %s" % (len(audioClip.component), audioClip.component))
		try:
			audioGameObject = audioClip.component[1]["component"].resolve()
			# dump(audioGameObject, 2)
			if audioGameObject["m_CardSoundData"]["m_AudioSource"] is not None:
				# print("\t\t\t audioSource %s" % (audioGameObject["m_CardSoundData"]["m_AudioSource"]))
				audioSource = audioGameObject["m_CardSoundData"]["m_AudioSource"].resolve()
				audioClipGuid = audioSource.game_object.resolve().component[2]["component"].resolve()["m_AudioClip"]
				# print("\t\t\t audioClipGuid %s" % (audioClipGuid))
				audioFileName = audioClipGuid.split(":")[0].split(".")[0]
				# print("\t\t\t audioFileName %s" % (audioFileName))
				if audioFileName and len(audioFileName) > 1:
					return audioFileName + ".ogg"
		except Exception as e:
			print("issue handling card with audioclip component %s " % (audioClip.component))
			print("%s" % e)
	return ''


def findAudios(audioClip, cardAudios, level, iteratedValues):
	# print("\t finding audios %s" % audioClip)
	if hasattr(audioClip, "component"):
		for index, elem in enumerate(audioClip.component):
			# print("\t\t has component %s, %s" % (index, elem))
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
			# print("\t\t audioClip %s, %s, %s" % (index, key, value))
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
		# print("\t\t has m_AudioClip %s" % (audioClip["m_AudioClip"]))
		add_to_audio(cardAudios, audioClip["m_AudioClip"])
		return
	if isinstance(audioClip, list):
		for elem in audioClip:
			# print("\t\t adding elem in audioClip %s" % elem)
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
		# print("\t\t adding _obj")
		findAudios(audioClip._obj, cardAudios, level + 1, iteratedValues)
		return
	if type(audioClip) in (int, float, bool, str):
		# print("\t\t invalid type")
		return
	if audioClip is None:
		# print("\t\t invalid None")
		return
	try:
		# print("\t resolving elem %s" % elem)
		resolved = elem.resolve()
		if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
			add_to_audio(cardAudios, resolved["m_AudioClip"])
		if elem.path_id not in iteratedValues:
			# print("\t\t itearting on path id %s" % elem.path_id)
			iteratedValues.append(elem.path_id)
			findAudios(resolved, cardAudios, level + 1, iteratedValues)
		return
	except:
		return


def add_to_audio(cardAudios, audioElement):
	trimmed = audioElement.split(".")[0]
	# print("\t\t\t add_to_audio %s" % trimmed)
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
		name = names[leaf["fileNameIndex"]]
		guid_to_path[guid] = path + "/" + name
		if guid == "b2f0dc3d643ccc149905ba94455a5d55":
			print("GOT IT!!!!!!!! %s" % (guid_to_path[guid]))

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
