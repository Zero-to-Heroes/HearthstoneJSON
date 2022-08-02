#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser
from collections import Counter

import UnityPy
from pydub import AudioSegment
from UnityPy.enums import ClassIDType


def main():
	p = ArgumentParser()
	p.add_argument("src")
	args = p.parse_args(sys.argv[1:])
	for root, dirs, files in os.walk(args.src):
		for file_name in files:
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			env = UnityPy.load(file_path)
			extract_assets(env)



def extract_assets(env):
	# iterate over assets
	for asset in env.assets:
		# assets without container / internal path will be ignored for now
		if not asset.container:
			continue

		items = asset.container.items()
		# print("items %s" % items)
		for key, obj in items:
			if obj.type == ClassIDType.AudioClip:
				# print("asset %s" % asset)
				# print("key %s" % key)
				# print("obj %s" % obj)
				export_obj(obj)
				# return


def export_obj(obj):
	try:
		data = obj.read()
	except:
		print("could not read audio clip %s " % obj)
		return

	# print("data %s" % data)
	# print("m_AudioData %s" % data.m_AudioData)
	samples = data.samples
	# print("samples %s" % len(samples))
	for name, data in samples.items():
		# print("sample %s, %s" % (name, len(data)))
		wav_file_name = f"out/sounds_wav/{name}"
		with open(wav_file_name, "wb") as f:
			f.write(data)
		sound = AudioSegment.from_wav(wav_file_name)
		base_file_name = os.path.splitext(name)[0].replace(" ", "")
		ogg_file_name = f"out/sounds/{base_file_name}.ogg"
		sound.export(ogg_file_name, format="ogg")


if __name__ == '__main__':
	main()
