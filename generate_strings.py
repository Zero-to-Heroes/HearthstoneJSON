#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

from hearthstone.enums import Locale
from hearthstone.stringsfile import load
from hearthstone_data import get_strings_file


FILENAMES = [
	"GAMEPLAY_AUDIO.txt",
	"GAMEPLAY.txt",
	"GLOBAL.txt",
	"GLUE.txt",
	"MISSION_AUDIO.txt",
	"MISSION.txt",
	"PRESENCE.txt",
	"TUTORIAL_AUDIO.txt",
	"TUTORIAL.txt",
]


def convert_strings_data(data):
	return {k: v.get("TEXT", "") for k, v in data.items()}


def main():
	parser = ArgumentParser()
	parser.add_argument(
		"-o", "--output-dir",
		type=str,
		default="out",
		help="Output directory"
	)
	args = parser.parse_args(sys.argv[1:])

	for locale in Locale:
		if locale.unused:
			continue

		basedir = os.path.join(args.output_dir, locale.name)
		if not os.path.exists(basedir):
			os.makedirs(basedir)

		for filename in FILENAMES:
			strings_path = get_strings_file(locale.name, filename=filename)
			with open(strings_path, "r", encoding="utf-8-sig") as f:
				strings_data = convert_strings_data(load(f))

			output_filename = os.path.join(basedir, filename.replace(".txt", ".json"))
			with open(output_filename, "w") as f:
				json.dump(strings_data, f)


if __name__ == "__main__":
	main()
