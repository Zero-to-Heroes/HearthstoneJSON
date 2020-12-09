#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import yaml

import unitypack
from unitypack.asset import Asset
from unitypack.object import ObjectPointer


def handle_asset(asset):
	for id, obj in asset.objects.items():
		d = obj.read()
		# Not sure why, but if you don't do this you end up with read errors. Maybe the tree needs to be
		# fully traversed first so that references are resolved or something?
		output = yaml.dump(d)
		if isinstance(d, dict):
			# print("is dict! %s: %s" % (id, d))
			if "m_Name" in d and d["m_Name"] is not "":
				# print("name %s" % d["m_Name"])
				if d["m_Name"] == "ACHIEVEMENT":
					# print("\tfound achievments")
					records = d["Records"]
					achievements = handle_records(records)
					# print("returning")
					return achievements
	# print("return empty")
	return []

def handle_records(records):
	achievements = []
	for record in records:
		achievements.append(handle_record(record))
	return achievements

def handle_record(record):
	# print("handling achievement %s" % record["m_name"]["m_locValues"][0])
	achievement = {
		"id": record["m_ID"],
		"sectionId": record["m_achievementSectionId"],
		"sortOrder": record["m_sortOrder"],
		"enabled": record["m_enabled"],
		"name": record["m_name"]["m_locValues"][0],
		"description": record["m_description"]["m_locValues"][0],
		"quota": record["m_quota"],
		"points": record["m_points"],
		"rewardTrackXp": record["m_rewardTrackXp"],
		"rewardListId": record["m_rewardListId"],
		"nextTierId": record["m_nextTierId"],
	}
	return achievement

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


def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+")
	p.add_argument("-s", "--strip", action="store_true", help="Strip extractable data")
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

	achievements = build_achievements(args.files)
	# print("achievements: %s" % achievements)

	with open('./hs-achievements.json', 'w') as resultFile:
		resultFile.write(json.dumps(achievements))


def build_achievements(files):
	for file in files:
		if file.endswith(".assets"):
			with open(file, "rb") as f:
				asset = Asset.from_file(f)
				achievements = handle_asset(asset)
				if len(achievements) > 0:
					# print("returning with achievements: %s" % len(achievements))
					return achievements
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)
			for asset in bundle.assets:
				achievements = handle_asset(asset)
				if len(achievements) > 0:
					# print("returning with achievements: %s" % len(achievements))
					return achievements

if __name__ == "__main__":
	main()
