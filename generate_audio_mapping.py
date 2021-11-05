#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import UnityPy
from UnityPy.enums import ClassIDType


# ./generate_audio.py /e/t > out.txt
def main():
	p = ArgumentParser()
	p.add_argument("src")
	args = p.parse_args(sys.argv[1:])

	sound_effects = extract_info(args.src)
	with open('./ref/sound_effects.json', 'w') as resultFile:
		resultFile.write(json.dumps(sound_effects))


def extract_info(src):
	audioClips = {}
	cards = {}

	for root, dirs, files in os.walk(src):
		for file_name in files:
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			env = UnityPy.load(file_path)
			handle_asset(env, audioClips, cards)

	for root, dirs, files in os.walk(src):
		for file_name in files:
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			env = UnityPy.load(file_path)
			handle_gameobject(env, audioClips, cards)

	return cards


def handle_asset(env, audioClips, cards):
	for obj in env.objects:
		if obj.type == ClassIDType.AssetBundle:
			data = obj.read()
			container = data.m_Container
			for path, asset in container.items():
				audioClips[path] = asset.asset

 
def handle_gameobject(env, audioClips, cards):
	for obj in env.objects:
		if obj.type == ClassIDType.GameObject:
			data = obj.read()
			cardid = data.name

			print("cardid: %s" % cardid)
			if len(data.m_Components) < 2:
				continue

			monoBehavior = data.m_Components[1]
			carddef = monoBehavior.read()
			
			play_effect_def = carddef.get("m_PlayEffectDef")
			if not play_effect_def:
				# Sometimes there's multiple per cardid, we remove the ones without art
				continue

			card = {}
			play_sounds = extract_sound_file_names(audioClips, carddef, "m_PlayEffectDef")
			if len(play_sounds) > 0:
				card["BASIC_play"] = play_sounds

			attack_sounds = extract_sound_file_names(audioClips, carddef, "m_AttackEffectDef")
			if len(attack_sounds) > 0:
				card["BASIC_attack"] = attack_sounds

			death_sounds = extract_sound_file_names(audioClips, carddef, "m_DeathEffectDef")
			if len(death_sounds) > 0:
				card["BASIC_death"] = death_sounds
				
			emote_sounds = extract_emote_sounds(audioClips, carddef)
			for emoteSound in emote_sounds:
				card[emoteSound["key"]] = [emoteSound["value"]]

			cards[cardid] = card


def extract_sound_file_names(audioClips, carddef, node):
	result = []
	try:
		path = carddef.get(node)
		path = path["m_SoundSpellPaths"]
		for play_effect_path in path:
			if ":" in play_effect_path:
				play_effect_path = play_effect_path.split(":")[1]
				pptr = audioClips[play_effect_path]
				audio_clip = pptr.read()
				audio_game_object = audio_clip.m_Components[1].read()
				card_sound_data = audio_game_object.get("m_CardSoundData")
				audio_source_pptr = card_sound_data["m_AudioSource"]
				if audio_source_pptr is not None:
					audio_source = audio_source_pptr.read()
					game_object = audio_source.get("m_GameObject").read()
					components = game_object.m_Components
					monobehavior = components[2].read()
					audio_clip_guid = monobehavior.get("m_AudioClip")
					audio_file_name = audio_clip_guid.split(":")[0].split(".")[0]
					if audio_file_name and len(audio_file_name) > 1:
						result.append(audio_file_name + ".ogg")
	except:
		print("\tERROR when processing %s" % carddef.name)
	return result


def extract_emote_sounds(audioClips, carddef):
	sounds = []
	try:
		emoteSounds = carddef.get("m_EmoteDefs")
		for emoteSound in emoteSounds:
			updatedPath = emoteSound["m_emoteSoundSpellPath"]
			soundInfo = extract_emote_sound(audioClips, updatedPath)
			if len(soundInfo) > 0:
				sound = {}
				sound["key"] = emoteSound["m_emoteGameStringKey"]
				sound["value"] = soundInfo
				sounds.append(sound)
	except:
		print("\tERROR when processing %s" % carddef.name)

	return sounds


def extract_emote_sound(audioClips, updatedPath):
	try:
		if ":" in updatedPath:
			updatedPath = updatedPath.split(":")[1]
			pptr = audioClips[updatedPath]
			audio_clip = pptr.read()
			if len(audio_clip.m_Components) < 2:
				audio_game_object = audio_clip.m_Components[1].read()
				card_sound_data = audio_game_object.get("m_CardSoundData")
				audio_source_pptr = card_sound_data["m_AudioSource"]

				if audio_source_pptr is not None:
					audio_source = audio_source_pptr.read()
					game_object = audio_source.get("m_GameObject").read()
					components = game_object.m_Components
					if len(components) > 2:
						monobehavior = components[2].read()
						audio_clip_guid = monobehavior.get("m_AudioClip")
						audio_file_name = audio_clip_guid.split(":")[0].split(".")[0]
						if audio_file_name and len(audio_file_name) > 1:
							return audio_file_name + ".ogg"
	except:
		print("\tERROR when processing %s" % updatedPath)
	return ''

def add_to_audio(cardAudios, audioElement):
	trimmed = audioElement.split(".")[0]
	if len(trimmed) > 0 and trimmed not in cardAudios:
		cardAudios.append(trimmed)


if __name__ == "__main__":
	main()
