#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import unitypack
import yaml
from unitypack.asset import Asset
from unitypack.object import ObjectPointer

# Generate the enums that are not present in the decompiled files
# Namely, Boards, Sets and Scenarios. Maybe Booster as well?

boards = []
boosters = []
scenarios = []

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

	build_enums(args.files)
	with open('./ref/boards.json', 'w') as resultFile:
		resultFile.write(json.dumps(boards))
	with open('./ref/boosters.json', 'w') as resultFile:
		resultFile.write(json.dumps(boosters))
	with open('./ref/scenarios.json', 'w') as resultFile:
		resultFile.write(json.dumps(scenarios))


def build_enums(files):
	for file in files:
		if file.endswith(".assets"):
			with open(file, "rb") as f:
				asset = Asset.from_file(f)
				handle_asset(asset)
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)
			for asset in bundle.assets:
				handle_asset(asset)


def handle_asset(asset):
	for id, obj in asset.objects.items():
		if obj.type == "AnimationClip":
			# There are issues reading animation clips, and we don't need them for cards
			continue

		try: 
			d = obj.read()
		except Exception as e:
			print("Could not read asset %s, %s, %s, %s" % (id, obj, asset, e))
			raise e

		if isinstance(d, dict):
			# print("is dict! %s: %s" % (id, d))
			if "m_Name" in d and d["m_Name"] is not "":
				# print("considering %s" % d["m_Name"])
				if d["m_Name"] in ["BOOSTER"]:
					# This is actually interesting, and has all the info about booster sets. Maybe use this to build the 
					# BoosterType enum?
					# Unfortunately, some data is missing, so it will have to be handled manually in any case
					# output = yaml.dump(d)
					# print(output)
					# records = d["Records"]
					# handle_boosters(records)
					a = 1
				elif d["m_Name"] in ["BOARD"]:
					# Same here, we can probably use this to build the BOARD enum
					# output = yaml.dump(d)
					# print(output)
					records = d["Records"]
					handle_boards(records)
				elif d["m_Name"] in ["SCENARIO"]:
					# Same here, can probably use it to build the Scenario enum instead of mapping everything by hand
					# output = yaml.dump(d)
					# print(output)
					if "Records" in d:
						records = d["Records"]
						handle_scenarios(records)


def handle_scenarios(records):
	for record in records:
		handle_scenario(record)

def handle_scenario(record):
	scenarios.append({
		"id": record["m_ID"],
		"name": record["m_noteDesc"],
	})


def handle_boosters(records):
	for record in records:
		handle_booster(record)

def handle_booster(record):
	locs = record["m_name"]["m_locValues"]
	if len(locs) == 0:
		print("\nMissing locs for booster")
		print(yaml.dump(record))
		return

	boosters.append({
		"id": record["m_ID"],
		"name": locs[0],
	})


def handle_boards(records):
	for record in records:
		handle_board(record)

def handle_board(record):
	boards.append({
		"id": record["m_ID"],
		"name": record["m_noteDesc"],
	})



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


def dump(obj, level):
  for attr in dir(obj):
    print("\t" * level, "obj.%s = %r" % (attr, getattr(obj, attr)))

if __name__ == "__main__":
	main()
