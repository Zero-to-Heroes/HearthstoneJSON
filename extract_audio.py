#!/usr/bin/env python
import json
import os
import sys
import datetime
from argparse import ArgumentParser
from collections import Counter

import UnityPy
from pydub import AudioSegment
from UnityPy.enums import ClassIDType

locales = [
	'enUS',
	'deDE',
	'esES',
	'esMX',
	'frFR',
	'itIT',
	'jaJP',
	'koKR',
	'plPL',
	'ptBR',
	'ruRU',
	'thTH',
	'zhCN',
	'zhTW',
]

import sys

# save the original print function
original_print = print

def print_with_timestamp(*args, **kwargs):
    original_print(f"[{datetime.datetime.now()}]", *args, **kwargs)

# replace print function with the new one
print = print_with_timestamp

class Logger(object):
    def __init__(self, logFile):
        self.terminal = sys.stdout
        self.log = open(logFile, "a")
   
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass    

sys.stdout = Logger("extract_audio.log")

def main():
	os.makedirs(os.path.dirname(f"out/sounds_wav/"), exist_ok=True)
	os.makedirs(os.path.dirname(f"out/sounds_wav/common/"), exist_ok=True)
	os.makedirs(os.path.dirname(f"out/sounds/common/"), exist_ok=True)
	for loc in locales:
		os.makedirs(os.path.dirname(f"out/sounds/{loc}/"), exist_ok=True)
		os.makedirs(os.path.dirname(f"out/sounds_wav/{loc}/"), exist_ok=True)
		
	p = ArgumentParser()
	p.add_argument("src")
	args = p.parse_args(sys.argv[1:])
	for root, dirs, files in os.walk(args.src):
		for file_name in files:
			if "sound" not in file_name.lower() and "audio" not in file_name.lower():
				# print("skipping %s" % file_name)
				continue

			# generate file_path
			file_path = os.path.join(root, file_name)
			env = UnityPy.load(file_path)
			print("handling %s" % file_path)

			current_loc = 'common'
			for loc in locales:
				if ("_" + loc.lower() + "-") in file_path.lower():
					current_loc = loc
					# print("current_loc %s" % current_loc)
					# print("file path %s" % file_path)

			extract_assets(env, current_loc)



def extract_assets(env, current_loc):
	# iterate over assets
	for asset in env.assets:
		# assets without container / internal path will be ignored for now
		if not asset.container:
			continue

		# if hasattr(asset, "path"):
		# 	print("considering %s" % asset.path)

		for path, obj in asset.container.items():
			# print("considering further %s, %s" % (path, obj))
			if obj.type == ClassIDType.AudioClip:
				# print("asset %s" % asset)
				# print("key %s" % key)
				# print("obj %s" % obj)
				export_obj(path, obj, current_loc)
				# return


def export_obj(path, obj, current_loc):
	try:
		data = obj.read()
	except:
		print("could not read audio clip %s " % obj)
		return

	# print("data %s" % data)
	# print("m_AudioData %s" % data.m_AudioData)
	samples = []
	try:
		samples = data.samples
	except Exception as e:
		print("could not extract samples from %s " % data)
		print("exception %s " % e)
		return
	
	for loc in locales:
		if ("/" + loc.lower() + "/") in path.lower():
			current_loc = loc		
	
	# print("samples %s" % len(samples))
	for name, data in samples.items():
		# print("sample %s, %s" % (name, len(data)))
		base_file_name = os.path.splitext(name)[0].replace(" ", "")
		# if "VO_EX1_383_Play_01" not in base_file_name:
		# 	continue

		wav_file_name = f"out/sounds_wav/{current_loc}/{base_file_name}.wav"
		ogg_file_name = f"out/sounds/{current_loc}/{base_file_name}.ogg"
		# print("base_file_name %s" % base_file_name)
		# print("wav_file_name %s" % wav_file_name)
		# print("locale %s" % current_loc)
		# print("path %s" % path)

		# print("warning, this should be uncommented")
		if os.path.exists(wav_file_name):
			# print("\t file already exists, continuing")
			continue

		try:
			with open(wav_file_name, "wb") as f:
				print("extracting wav file %s from %s" % (wav_file_name, path))
				f.write(data)
			print("\t exporting ogg file %s" % ogg_file_name)
			sound = AudioSegment.from_wav(wav_file_name)		
			sound.export(ogg_file_name, format="ogg")
		except Exception as e:
			print("could not extract wav file %s from %s" % (wav_file_name, path))
			print("exception %s " % e)

		if os.path.exists(ogg_file_name):
			print("\togg file %s successfully created" % ogg_file_name)
		else:
			print("\togg file %s not found" % ogg_file_name)
			raise Exception("ogg file %s not found" % ogg_file_name)


if __name__ == '__main__':
	main()
