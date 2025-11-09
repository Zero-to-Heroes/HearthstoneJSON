#!/usr/bin/env python
import tracemalloc
import gc
import json
import os
import sys
import yaml
import UnityPy
from argparse import ArgumentParser
from typing import List, cast, Dict

from PIL import Image, ImageOps 
from UnityPy import Environment
from UnityPy.enums import ClassIDType
from UnityPy.helpers import TypeTreeHelper
from UnityPy.classes import PPtr, GameObject, ComponentPair, Tuple, Component, MonoBehaviour, Material, UnityPropertySheet, AssetBundle

class Logger(object):
    def __init__(self, logFile):
        self.terminal = sys.stdout
        self.log = open(logFile, "w")
   
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass    

# sys.stdout = Logger("generate_audio_mapping.log")

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
	
	print("Loading environment")
	env: Environment = UnityPy.load(src)
 
	print("BUilding audio clips mapping")
	add_audio_clip_mapping(env, audioClips)		
 
	print("BUilding cards map")
	cards_map = build_cards_map(env)	
   
	print("Building mapping")
	cards = add_card_audio_mapping(env, cards_map, audioClips)
	print("cards %s" % len(cards))

	print("Writing filee")
	fp = os.path.join(f"ref/sound_effects.json")
	with open(fp, "wt", encoding = "utf8") as f:
		json.dump(cards, f, ensure_ascii = False, indent = 4)
  
	print("Job's done")
	return cards


def add_audio_clip_mapping(env: Environment, audioClips):
	for obj in env.objects:
		if obj.type == ClassIDType.AssetBundle:
			data = cast(AssetBundle, obj.read())
			container = data.m_Container
			for path, asset in container:
				audioClips[path] = asset.asset

 
def build_cards_map(env: Environment) -> Dict[str, str]:
	for obj in env.objects:
		if obj.type == ClassIDType.MonoBehaviour:
			dataM: MonoBehaviour = cast(MonoBehaviour, obj.read())
			if dataM.m_Name == "cards_map":
				tree = dataM.map
				keys = tree.keys
				values = tree.values
				print("keys: %s" % len(keys))
				print("values: %s" % len(values))
				# Build a dictionary of key => prefabid
				cards_map = {}
				for cardid, value in zip(keys, values):
					# if cardid != "SC_004":
					# 	continue
					# Only keep the id of the prefab, which means what is after prefab:
					asset_id = value.split("prefab:")[1]
					cards_map[cardid] = asset_id
				return cards_map


def add_card_audio_mapping(env: Environment, cards_map: Dict[str, str], audioClips):
	cards = {}
	current_card_idx = -1
	for cardid, prefabid in cards_map.items():
		current_card_idx += 1
		# try:
		# if current_card_idx < 1200:
		# 	continue
		prefab_pptr = env.container[prefabid]
		print("card %s: %s" % (current_card_idx, cardid))
		prefab: GameObject = prefab_pptr.read()
		components: List[ComponentPair] = prefab.m_Component

		for component in components:
			# print("component: %s" % component)
			component_pptr = component.component
			if component_pptr.type.name == "MonoBehaviour":
				# monobehavior_data = component_pptr.deref()
				# card_def = monobehavior_data.read_typetree()
				# json.dump(card_def, sys.stdout, ensure_ascii = False, indent = 4)
				card_def = component_pptr.read()
				if not hasattr(card_def, "m_PlayEffectDef"):
					print("\tskipping %s, no m_PlayEffectDef" % cardid)
					continue

				card = {}

				play_sounds = extract_sound_file_names(audioClips, card_def, "m_PlayEffectDef", cardid)
				# print("\tplay_sounds")
				if len(play_sounds) > 0:
					card["BASIC_play"] = play_sounds

				attack_sounds = extract_sound_file_names(audioClips, card_def, "m_AttackEffectDef", cardid)
				# print("\tattack_sounds")
				if len(attack_sounds) > 0:
					card["BASIC_attack"] = attack_sounds

				death_sounds = extract_sound_file_names(audioClips, card_def, "m_DeathEffectDef", cardid)
				# print("\tdeath_sounds")
				if len(death_sounds) > 0:
					card["BASIC_death"] = death_sounds
					
				emote_sounds = extract_emote_sounds(audioClips, card_def, cardid)
				# print("\temote_sounds")
				for emoteSound in emote_sounds:
					card[emoteSound["key"]] = {
						emoteSound["key"]: {
							"mainSounds": [emoteSound["value"]]
						}
					}
				
				# print("\tbuilt card %s" % len(card))
				cards[cardid] = card
		# except Exception as e:
		# 	print("ERROR when processing card %s" % cardid)
		# 	print("\t" + str(e))
		# 	continue
	print("done processing cards")
	return cards


def extract_sound_file_names(audioClips, card_def, nodeName, card_id):
	result = {}
	sound_root_node = card_def.__getattribute__(nodeName)
	# print("\tsound_root_node %s" % sound_root_node)
	sound_spell_paths = sound_root_node.__getattribute__("m_SoundSpellPaths")
	# print("\tsound_spell_paths %s" % sound_spell_paths)
	for sound_prefab_id_long in sound_spell_paths:
		extract_sound(audioClips, sound_prefab_id_long, result)
	return result
  
  
def extract_sound(audio_clips, sound_prefab_id_long, result):
	# print("\t\tconsidering path %s" % sound_prefab_id_long)
	if not ":" in sound_prefab_id_long:
		return

	effectKey = sound_prefab_id_long.split(":")[0].split(".prefab")[0].replace(" ", "")
	# print("\t\teffectKey %s" % effectKey)
	if effectKey in result:
		effect = result[effectKey]
	else:
		effect = {
			"mainSounds": [],
			"randomSounds": []
		}
	# print('\t\teffect %s' % effect) 
	result[effectKey] = effect
 
	sound_prefab_id = sound_prefab_id_long.split(":")[1]
	try:
		pptr: PPtr = cast(PPtr, audio_clips[sound_prefab_id])
	except:
		print("Missing sound prefab %s" % sound_prefab_id)
		return
  
	# print("\t\tpptr %s" % pptr)
	audio_clip: GameObject = cast(GameObject, pptr.read())
	# print("\t\taudio_clip %s" % audio_clip)
	for component in audio_clip.m_Component:
		# print("\t\tcomponent %s" % component)
		component_pptr: PPtr = cast(PPtr, component.component)
		# print("\t\tcomponent_pptr %s" % component_pptr.type.name)	
		if component_pptr.type.name == "MonoBehaviour":
			sound_def = component_pptr.read()
			handle_audio_clip_component(sound_def, effect, effectKey)
  
  
def handle_audio_clip_component(sound_def, effect, effectKey):  
	card_sound_data = sound_def.__getattribute__("m_CardSoundData")
	# print("\t\tcard_sound_data %s" % card_sound_data)   
	audio_source_pptr = card_sound_data.__getattribute__("m_AudioSource")
	# print("\t\taudio_source_pptr %s" % audio_source_pptr)
	if audio_source_pptr is None:
		return
	try:
		# This can happen because some spells have a pointer leading to nothing because they inherit a base card object
		audio_source = audio_source_pptr.read()
	except:
		effect["mainSounds"].append(effectKey + ".ogg")
		return

	# print("\t\taudio_source %s" % audio_source)
	audio_source_game_object = cast(GameObject, audio_source.__getattribute__("m_GameObject").read())
	for component in audio_source_game_object.m_Component:
		# print("\t\t\tcomponent %s" % component)
		component_pptr: PPtr = cast(PPtr, component.component)
		# print("\t\t\tcomponent_pptr %s" % component_pptr.type.name)	
		if component_pptr.type.name == "MonoBehaviour":
			monobehavior = component_pptr.read()
			# print("\t\t\tmonobehavior %s" % monobehavior)
			# Standard audio clips
			audio_clip_guid = monobehavior.__getattribute__("m_AudioClip")
			audio_file_name = audio_clip_guid.split(":")[0].split(".")[0]
			# print("\t\t\taudio_file_name %s" % audio_file_name)
			if audio_file_name and len(audio_file_name) > 1:
				effect["mainSounds"].append(audio_file_name.replace(" ", "") + ".ogg")

			# "Random" audio clips
			random_clips = monobehavior.__getattribute__("m_RandomClips")
			if random_clips is not None and len(random_clips) > 0:
				for clip in random_clips:
					# print("\t\t\tlooking at random clip %s" % clip)
					random_audio_clip_guid = clip.__getattribute__("m_Clip")
					random_audio_file_name = random_audio_clip_guid.split(":")[0].split(".")[0]
					# print("\t\t\taudio_file_name %s" % random_audio_file_name)
					if random_audio_file_name and len(random_audio_file_name) > 1:
						effect["randomSounds"].append({
							"sound": random_audio_file_name.replace(" ", "") + ".ogg",
							"weight": clip.__getattribute__("m_Weight")
						})
		


def extract_emote_sounds(audioClips, carddef, card_id):
	sounds = []
	emoteSounds = carddef.__getattribute__("m_EmoteDefs")
	for emoteSound in emoteSounds:
		updatedPath = emoteSound.__getattribute__("m_emoteSoundSpellPath")
		soundInfo = extract_emote_sound(audioClips, updatedPath, card_id)
		if len(soundInfo) > 0:
			sound = {}
			sound["key"] = emoteSound.__getattribute__("m_emoteGameStringKey").replace(" ", "")
			sound["value"] = soundInfo.replace(" ", "")
			sounds.append(sound)

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
				card_sound_data = audio_game_object.__getattribute__("m_CardSoundData")
				audio_source_pptr = card_sound_data.__getattribute__("m_AudioSource")

				if audio_source_pptr is not None:
					# print(audio_source_pptr)
					audio_source = audio_source_pptr.read()
					# print(audio_source["m_GameObject"])
					game_object = audio_source.__getattribute__("m_GameObject").read()
					components = game_object.m_Components
					if len(components) > 2:
						# print(components[2])
						# print(components[2].dump_typetree())
						monobehavior = components[2].read()
						audio_clip_guid = monobehavior.__getattribute__("m_AudioClip")
						audio_file_name = audio_clip_guid.split(":")[0].split(".")[0].replace(" ", "")
						if audio_file_name and len(audio_file_name) > 1:
							return audio_file_name + ".ogg"
	except Exception as e:
		print("ERROR when processing extract_emote_sound %s, %s" % (card_id, updatedPath))
		print("\t" + str(e))
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
