#!/usr/bin/env python
import json
import os
import sys
import yaml
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

	env = UnityPy.load(src)
	handle_asset(env, audioClips, cards)
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

			# if cardid != "DRGA_BOSS_08h":
			# 	continue

			# print("cardid: %s" % cardid)
			# print(obj.dump_typetree())
			if len(data.m_Components) < 2:
				continue

			monoBehavior = data.m_Components[1]
			carddef = monoBehavior.read()
			# print("carddef %s " % type(carddef).__name__)
			# if type(carddef).__name__ == "NodeHelper":
			# 	print(carddef)
			# else:
			# 	print(carddef)			
			# print(carddef.dump_typetree())
			try:
				play_effect_def = carddef.get("m_PlayEffectDef")
			except:
				try:
					play_effect_def = carddef["m_PlayEffectDef"]
				except:
					continue

			if not play_effect_def:
				# print("no play_effect_def")
				# Sometimes there's multiple per cardid, we remove the ones without art
				continue

			card = {}

			play_sounds = extract_sound_file_names(audioClips, carddef, "m_PlayEffectDef", cardid)
			# print("play sounds")
			# print(play_sounds)
			if len(play_sounds) > 0:
				card["BASIC_play"] = play_sounds

			# print("will extract attack")
			attack_sounds = extract_sound_file_names(audioClips, carddef, "m_AttackEffectDef", cardid)
			if len(attack_sounds) > 0:
				card["BASIC_attack"] = attack_sounds

			death_sounds = extract_sound_file_names(audioClips, carddef, "m_DeathEffectDef", cardid)
			if len(death_sounds) > 0:
				card["BASIC_death"] = death_sounds
				
			emote_sounds = extract_emote_sounds(audioClips, carddef, cardid)
			for emoteSound in emote_sounds:
				card[emoteSound["key"]] = [emoteSound["value"]]

			cards[cardid] = card


def extract_sound_file_names(audioClips, carddef, node, card_id):
	result = {}
	path = carddef.get(node)
	# print("path")
	# print(path)
	path = path["m_SoundSpellPaths"]
	for play_effect_path in path:
		# print("considering path %s" % play_effect_path)
		try:
			if ":" in play_effect_path:
				effectKey = play_effect_path.split(":")[0].split(".prefab")[0].replace(" ", "")
				print("effectKey %s" % effectKey)
				if effectKey in result:
					effect = result[effectKey]
				else:
					effect = {
						"mainSounds": [],
						"randomSounds": []
					}
				# print('effect %s' % effect)
				result[effectKey] = effect
				play_effect_path = play_effect_path.split(":")[1]
				# print(json.dumps(play_effect_path))	
				pptr = audioClips[play_effect_path]
				# print("pptr")
				# print(pptr)
				audio_clip = pptr.read()
				# print("audio_clip")
				# print(audio_clip.dump_typetree())
				audio_game_object = audio_clip.m_Components[1].read()
				card_sound_data = audio_game_object.get("m_CardSoundData")
				# print(card_sound_data)
				audio_source_pptr = card_sound_data["m_AudioSource"]
				if audio_source_pptr is not None:
					# print("audio_source_pptr")
					# print(audio_source_pptr)
					try:
						# This can happen because some spells have a pointer leading to nothing because they inherit a base card object
						audio_source = audio_source_pptr.read()
					except:
						effect["mainSounds"].append(effectKey + ".ogg")
						continue
					# print("audio_source")
					# print(audio_source)
					game_object = audio_source["m_GameObject"].read()
					components = game_object.m_Components
					# print("components")
					# print(components)
					monobehavior = components[2].read()
					# print("monobehvior")
					# print(monobehavior.dump_typetree())

					# Standard audio clips
					audio_clip_guid = monobehavior.get("m_AudioClip")
					audio_file_name = audio_clip_guid.split(":")[0].split(".")[0]
					# print("audio_file_name %s" % audio_file_name)
					if audio_file_name and len(audio_file_name) > 1:
						effect["mainSounds"].append(audio_file_name.replace(" ", "") + ".ogg")

					# "Random" audio clips
					random_clips = monobehavior.get("m_RandomClips")
					if random_clips is not None and len(random_clips) > 0:
						for clip in random_clips:
							# print("\tlooking at random clip %s" % clip)
							random_audio_clip_guid = clip["m_Clip"]
							random_audio_file_name = random_audio_clip_guid.split(":")[0].split(".")[0]
							# print("\taudio_file_name %s" % random_audio_file_name)
							if random_audio_file_name and len(random_audio_file_name) > 1:
								effect["randomSounds"].append({
									"sound": random_audio_file_name.replace(" ", "") + ".ogg",
									"weight": clip["m_Weight"]
								})
				else:
					print("no audio_source_pptr")
		except Exception as e:
			print("\tERROR when processing extract_sound_file_names %s, %s" % (card_id, carddef.name))
			print(e)
	return result


def extract_emote_sounds(audioClips, carddef, card_id):
	sounds = []
	try:
		emoteSounds = carddef.get("m_EmoteDefs")
		for emoteSound in emoteSounds:
			updatedPath = emoteSound["m_emoteSoundSpellPath"]
			soundInfo = extract_emote_sound(audioClips, updatedPath, card_id)
			if len(soundInfo) > 0:
				sound = {}
				sound["key"] = emoteSound["m_emoteGameStringKey"].replace(" ", "")
				sound["value"] = soundInfo.replace(" ", "")
				sounds.append(sound)
	except Exception as e:
		print("\tERROR when processing extract_emote_sounds %s, %s" % (card_id, carddef.name))
		print(e)

	return sounds


def extract_emote_sound(audioClips, updatedPath, card_id):
	try:
		if ":" in updatedPath:
			# print("considering path %s" % updatedPath)
			updatedPath = updatedPath.split(":")[1]
			# print("considering updatedPath %s" % updatedPath)
			# print("is in? %s" % (updatedPath in audioClips))
			if updatedPath not in audioClips:
				return ''
			pptr = audioClips[updatedPath]
			# print('pptr')
			# print(pptr)
			audio_clip = pptr.read()
			if audio_clip is not None and len(audio_clip.m_Components) >= 2:
				# print(audio_clip.m_Components[1])
				audio_game_object = audio_clip.m_Components[1].read()
				card_sound_data = audio_game_object.get("m_CardSoundData")
				audio_source_pptr = card_sound_data["m_AudioSource"]

				if audio_source_pptr is not None:
					# print(audio_source_pptr)
					audio_source = audio_source_pptr.read()
					# print(audio_source["m_GameObject"])
					game_object = audio_source["m_GameObject"].read()
					components = game_object.m_Components
					if len(components) > 2:
						# print(components[2])
						# print(components[2].dump_typetree())
						monobehavior = components[2].read()
						audio_clip_guid = monobehavior.get("m_AudioClip")
						audio_file_name = audio_clip_guid.split(":")[0].split(".")[0].replace(" ", "")
						if audio_file_name and len(audio_file_name) > 1:
							return audio_file_name + ".ogg"
	except Exception as e:
		print("\tERROR when processing extract_emote_sound %s, %s" % (card_id, updatedPath))
		print(e)
	return ''

def add_to_audio(cardAudios, audioElement):
	trimmed = audioElement.split(".")[0]
	if len(trimmed) > 0 and trimmed not in cardAudios:
		cardAudios.append(trimmed)


def dump(obj, level=1):
	for attr in dir(obj):
		print("\t" * level, "obj.%s = %r" % (attr, getattr(obj, attr)))

if __name__ == "__main__":
	main()
