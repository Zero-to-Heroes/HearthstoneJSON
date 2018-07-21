#!/usr/bin/env python
import re
import sys
from hearthstone.enums import Locale


def find_substring(s, search_space):
	return s in search_space or s.lower() in search_space


def find_locale(data, index):
	for loc in Locale.__members__:
		if loc == "UNKNOWN":
			continue

		search_space = data[index-100:index]
		if find_substring(loc, search_space):
			return loc

	raise RuntimeError("Could not find locale")


def pluck_carddefs_xml(data):
	end_match = re.search(r"</CardDefs>", data)
	if not end_match:
		raise RuntimeError("Could not find end of XML block")
	return data[:end_match.end()]


def write_file(filename, data):
	print("Writing to %r" % (filename))
	with open(filename, "w") as f:
		f.write(data)


def parse_bundle(f):
	data = f.read()
	decoded = data.decode("utf-8", "ignore")
	indices = [match.start() for match in re.finditer(r"<CardDefs>", decoded)]
	for index in indices:
		locale = find_locale(decoded, index)
		xml = pluck_carddefs_xml(decoded[index:])
		write_file(locale + ".xml", xml)


def main():
	bundle = sys.argv[1]
	with open(bundle, "rb") as f:
		parse_bundle(f)


if __name__ == "__main__":
	main()
