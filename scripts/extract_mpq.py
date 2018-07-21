#!/usr/bin/env python
import os
import re
import sys
import mpq
from hearthstone import enums


EXTRACT = [
	"Hearthstone.exe",
	"manifest-cards.csv",
	"Data/PlayErrors.xml",
	"Data/cards.unity3d",
	"Data/cards0.unity3d",
	"Data/cards1.unity3d",
	"Data/cardxml0.unity3d",
	"Data/Win/cardxml0.unity3d",
	"Data/Win/cards0.unity3d",
	"Data/Win/cards1.unity3d",
	"Data/Win/cards2.unity3d",
	"Hearthstone_Data/mainData",
	"Hearthstone_Data/Managed/Assembly-CSharp.dll",
	"Hearthstone_Data/Managed/Assembly-CSharp-firstpass.dll",
	"DBF/ACHIEVE.xml",
	"DBF/ADVENTURE.xml",
	"DBF/ADVENTURE_DATA.xml",
	"DBF/ADVENTURE_MISSION.xml",
	"DBF/ADVENTURE_MODE.xml",
	"DBF/BANNER.xml",
	"DBF/BOARD.xml",
	"DBF/BOOSTER.xml",
	"DBF/CARD.xml",
	"DBF/CARD_BACK.xml",
	"DBF/FIXED_REWARD.xml",
	"DBF/FIXED_REWARD_ACTION.xml",
	"DBF/FIXED_REWARD_MAP.xml",
	"DBF/HERO.xml",
	"DBF/SCENARIO.xml",
	"DBF/SEASON.xml",
	"DBF/WING.xml",
]

STRINGS = [
	"CREDITS_2014.txt",
	"CREDITS_2015.txt",
	"GAMEPLAY_AUDIO.txt",
	"GAMEPLAY.txt",
	"GLOBAL.txt",
	"GLUE.txt",
	"MISSION_AUDIO.txt",
	"PRESENCE.txt",
	"TUTORIAL_AUDIO.txt",
	"TUTORIAL.txt",
]

MPQ_REGEX = re.compile(r"hs-(\d+)-(\d+)-Win-final.MPQ")


def extract(mpq, build, extract_to):
	def _extract(path):
		if path not in mpq:
			# print("Skipping %r (not found)" % (path))
			return
		data = mpq.open(path).read()
		if not data:
			print("Skipping %r (empty)" % (path))
			return
		extract_path = os.path.join(extract_to, str(build), path)
		dirname = os.path.dirname(extract_path)
		if not os.path.exists(dirname):
			os.makedirs(dirname)
		print("Writing to %r" % (extract_path))

		with open(extract_path, "wb") as f:
			f.write(data)

	for path in EXTRACT:
		_extract(path)

	for locale in enums.Locale:
		for filename in STRINGS:
			_extract("Strings/%s/%s" % (locale.name, filename))


def get_builds(basepath):
	basepath = os.path.join(basepath, "Updates")
	if not os.path.exists(basepath):
		# No build chain
		return {}
	builds = {}
	for path in os.listdir(basepath):
		sre = MPQ_REGEX.match(path)
		if sre:
			base, build = sre.groups()
			base = int(base)
			if base not in builds:
				builds[base] = []
			builds[base].append(int(build))
	return builds


def get_build_chains(builds):
	chains = []
	for base_build in builds[0]:
		chain = []

		def get_build_chain(build):
			chain.append(build)
			if build in builds:
				return get_build_chain(builds[build][0])
			return chain

		chains.append(get_build_chain(base_build))

	return chains


def extract_plain(path, extract_to, only=[]):
	build = re.search(r"(\d+)", path).groups()[0]
	mpqname = os.path.join(path, "base-Win.MPQ")
	print("Opening: %r" % (mpqname))
	base = mpq.MPQFile(mpqname)
	if only and build not in only:
		return
	extract(base, build, extract_to)


def extract_chain(path, chain, extract_to, only=[]):
	base_build = 0
	mpqname = os.path.join(path, "base-Win.MPQ")
	print("Opening: %r" % (mpqname))
	base = mpq.MPQFile(mpqname)
	for build in chain:
		mpqname = "hs-%i-%i-Win-final.MPQ" % (base_build, build)
		print("Opening: %r" % (mpqname))
		base.patch(os.path.join(path, "Updates", mpqname))
		base_build = build
		if only and build not in only:
			continue
		extract(base, build, extract_to)


def main():
	if len(sys.argv) < 3:
		print("Usage: %s <indir> <outdir>" % (sys.argv[0]))
		exit(1)

	base_path = sys.argv[1]
	extract_to = sys.argv[2]
	filter_builds = [int(x) for x in sys.argv[3:]]
	direct_builds = [3140, 3388, 3749, 4243, 4944]

	for build in direct_builds:
		path = os.path.join(base_path, "%i.direct" % (build))
		builds = get_builds(path)
		extract_plain(path, extract_to, only=filter_builds)
		if builds:
			chains = get_build_chains(builds)
			for chain in chains:
				extract_chain(path, chain, extract_to, only=filter_builds)


if __name__ == "__main__":
	main()
