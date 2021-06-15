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

# guid_to_path = {}

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
		if ("card" in bundle.path or "initial_base" in bundle.path) and ("cardtexture" not in bundle.path):
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
			for emoteSound in emoteSounds:
				card[emoteSound["key"]] = [emoteSound["value"]]

			if assigned == 0:
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
		updatedPath = playEffectPath
		if ":" in updatedPath:
			guid = updatedPath.split(":")[1]
		if updatedPath and len(updatedPath) > 1:
			if not updatedPath.startswith("final/"):
				updatedPath = "final/" + updatedPath
			try:
				audioClip = audioClips[updatedPath.lower()].resolve()
			except Exception as e:
				try :
					audioClip = audioClips[guid].resolve()
				except Exception as f:
					result.append(guid)
					continue
			audioGameObject = audioClip.component[1]["component"].resolve()
			if audioGameObject["m_CardSoundData"]["m_AudioSource"] is not None:
				audioSource = audioGameObject["m_CardSoundData"]["m_AudioSource"].resolve()
				audioClipGuid = audioSource.game_object.resolve().component[2]["component"].resolve()["m_AudioClip"]
				audioFileName = audioClipGuid.split(":")[0].split(".")[0]
				if audioFileName and len(audioFileName) > 1:
					result.append(audioFileName + ".ogg")

	return result


# Not handled anymore for now
def extract_spell_sounds(audioClips, carddef):
	otherPlayAudio = carddef["m_PlayEffectDef"]["m_SpellPath"]
	return []


def extract_emote_sounds(audioClips, carddef):
	sounds = []
	emoteSounds = carddef["m_EmoteDefs"]
	for emoteSound in emoteSounds:
		updatedPath = emoteSound["m_emoteSoundSpellPath"]
		soundInfo = extract_emote_sound(audioClips, updatedPath)
		if len(soundInfo) > 0:
			sound = {}
			sound["key"] = emoteSound["m_emoteGameStringKey"]
			sound["value"] = soundInfo
			sounds.append(sound)
	return sounds


def extract_emote_sound(audioClips, updatedPath):
	guid = ''
	if ":" in updatedPath:
		guid = updatedPath.split(":")[1]
	if updatedPath and len(updatedPath) > 1:
		if not updatedPath.startswith("final/"):
			updatedPath = "final/" + updatedPath
		try:
			audioClip = audioClips[updatedPath.lower()].resolve()
		except Exception as e:
			try :
				audioClip = audioClips[guid].resolve()
			except Exception as f:
				return ''
		try:
			audioGameObject = audioClip.component[1]["component"].resolve()
			if audioGameObject["m_CardSoundData"]["m_AudioSource"] is not None:
				audioSource = audioGameObject["m_CardSoundData"]["m_AudioSource"].resolve()
				audioClipGuid = audioSource.game_object.resolve().component[2]["component"].resolve()["m_AudioClip"]
				audioFileName = audioClipGuid.split(":")[0].split(".")[0]
				if audioFileName and len(audioFileName) > 1:
					return audioFileName + ".ogg"
		except Exception as e:
			print("\t\t\tissue handling card with audioclip component %s " % (audioClip.component))
			print("\t\t\t%s" % e)
	return ''


# Not handled anymore for now (too slow, and not really useful)
def findAudios(audioClip, cardAudios, level, iteratedValues):
	return


def add_to_audio(cardAudios, audioElement):
	trimmed = audioElement.split(".")[0]
	# print("\t\t\t add_to_audio %s" % trimmed)
	if len(trimmed) > 0 and trimmed not in cardAudios:
		cardAudios.append(trimmed)


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
