#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import unitypack
import yaml
from PIL import Image, ImageOps
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment
from unitypack.object import ObjectPointer
from unitypack.utils import extract_audioclip_samples

guid_to_path = {}

# ./generate_audio.py /e/t/*unity3d > out.txt
# works, but super slow
def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+")
	p.add_argument("-s", "--strip", action="store_true", help="Strip extractable data")
	p.add_argument("--as-asset", action="store_true", help="Force open files as Asset format")
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

	cards = extract_info(args.files)
	with open('./ref/sound_effects.json', 'w') as resultFile:
		resultFile.write(json.dumps(cards))


# def populate_guid_to_path(asset, audioClips):
# 	for id, obj in asset.objects.items():
# 		try:
# 			d = obj.read()

# 			for asset_info in d["m_assets"]:
# 				guid = asset_info["Guid"]
# 				print("\t\tHandling asset type: %s" % obj.type)
# 				path = asset_info["Path"]
# 				path = path.lower()
# 				if not path.startswith("final/"):
# 					path = "final/" + path
# 				if not path.startswith("final/assets"):
# 					continue
# 				guid_to_path[guid] = path
# 				audioClips[path] = asset_info
# 		except Exception as e:
# 			continue


def extract_info(files):
	audioClips = {}
	cards = {}
	print("Creating unity environment")
	env = UnityEnvironment()

	print("Loading files")
	for file in files:
		# print("\tloading %s" % file)
		f = open(file, "rb")
		env.load(f)

	print("handling rads")
	for bundle in env.bundles.values():
		# print("\tbundle rad %s" % bundle.path)
		if "rad_base" in bundle.path or "rad_enus" in bundle.path:
			for asset in bundle.assets:
				handle_rad_asset(asset, audioClips, cards)

	print("handling asset caching")
	for bundle in env.bundles.values():
		# print("\tbundle asset %s" % bundle.path)
		# if "sound" in bundle.path:
		for asset in bundle.assets:
			handle_asset(asset, audioClips, cards)

	print("parsing game objects")
	for bundle in env.bundles.values():
		# print("\tbundle gameobject %s" % bundle.path)
		if ("card" in bundle.path or "initial_base" in bundle.path) and ("cardtexture" not in bundle.path):
			# print(yaml.dump(bundle))		
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
				if not finalPath.startswith("final/"):
					finalPath = "final/" + finalPath
				audioClips[finalPath] = asset
				audioClips[path] = asset


def handle_rad_asset(asset, audioClips, cards):
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
				audioClips[finalPath] = asset
				audioClips[path] = asset


def handle_gameobject(asset, audioClips, cards):
	assigned = 0
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

			if assigned == 0:
				# print("\t\t\tassigned card")
				assigned = 1

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
				# print("\t\t\t could process %s" % (updatedPath))
			except Exception as e:
				try :
					# print("\t\t\t could not process %s" % (updatedPath))
					audioClip = audioClips[guid].resolve()
					# print("\t\t\t could process %s" % (updatedPath))
				except Exception as f:
					# print("\t\t\t\t could not process at all %s, %s" % (updatedPath, f))
					result.append(guid)
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
				# print("\t\t\t could process %s" % (playEffectPath))
			except Exception as e:
				try :
					# print("\t\t\t could not process %s, %s" % (playEffectPath, e))
					audioClip = audioClips[guid].resolve()
					# print("\t\t\t could process %s" % (playEffectPath))
				except Exception as f:
					# print("\t\t\t\t could not process at all %s, %s" % (playEffectPath, f))
					return [guid]
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
			audioClip = audioClips[updatedPath.lower()].resolve()
			# print("\t\t\t could process %s" % (updatedPath))
		except Exception as e:
			try :
				# print("\t\t\t could not process %s, %s" % (updatedPath, e))
				audioClip = audioClips[guid].resolve()
				# print("\t\t\t could process %s" % (updatedPath))
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
			print("\t\t\tissue handling card with audioclip component %s " % (audioClip.component))
			print("\t\t\t%s" % e)
	return ''


def findAudios(audioClip, cardAudios, level, iteratedValues):
	# TODO: temp test to check the speed without this recursive digging
	return
	# print("\t finding audios %s" % audioClip)
	if hasattr(audioClip, "component"):
		for index, elem in enumerate(audioClip.component):
			# print("\t\t has component %s, %s" % (index, elem))
			try:
				resolved = elem.resolve()
				if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
					print("found clip 1")
					print(yaml.dump(resolved))
					add_to_audio(cardAudios, resolved["m_AudioClip"])
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
				print("found clip 2")
				print(yaml.dump(value))
				add_to_audio(cardAudios, value)
			try:
				resolved = value.resolve()
				if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
					print("found clip 3")
					print(yaml.dump(resolved))
					add_to_audio(cardAudios, resolved["m_AudioClip"])
				if value.path_id not in iteratedValues:
					iteratedValues.append(value.path_id)
					findAudios(resolved, cardAudios, level + 1, iteratedValues)
			except:
				findAudios(value, cardAudios, level + 1, iteratedValues)
		return
	if hasattr(audioClip, "m_AudioClip") and audioClip["m_AudioClip"] is not None:
		# print("\t\t has m_AudioClip %s" % (audioClip["m_AudioClip"]))
		print("found clip 4")
		print(yaml.dump(audioClip["m_AudioClip"]))
		add_to_audio(cardAudios, audioClip["m_AudioClip"])
		return
	if isinstance(audioClip, list):
		for elem in audioClip:
			# print("\t\t adding elem in audioClip %s" % elem)
			try:
				resolved = elem.resolve()
				if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
					print("found clip 5")
					print(yaml.dump(resolved["m_AudioClip"]))
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
	# try:
	# 	# print("\t resolving elem %s" % elem)
	# 	resolved = elem.resolve()
	# 	if hasattr(resolved, "m_AudioClip") and resolved["m_AudioClip"] is not None:
	# 		add_to_audio(cardAudios, resolved["m_AudioClip"])
	# 	if elem.path_id not in iteratedValues:
	# 		# print("\t\t itearting on path id %s" % elem.path_id)
	# 		iteratedValues.append(elem.path_id)
	# 		findAudios(resolved, cardAudios, level + 1, iteratedValues)
	# 	return
	# except:
	# 	return


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


if __name__ == "__main__":
	main()
