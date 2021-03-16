# Ultimately not needed, because we can use Blizzard's API for that

#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import unitypack
import yaml
from unitypack.asset import Asset
from unitypack.object import ObjectPointer


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

	result = build_card_backs(args.files)
	# print("achievements: %s" % achievements)

	with open('./card_backs.json', 'w') as resultFile:
		resultFile.write(json.dumps(result))


def build_card_backs(files):
	for file in files:
		if file.endswith(".assets"):
			with open(file, "rb") as f:
				asset = Asset.from_file(f)
				result = handle_asset(asset)
				if result is not None:
					print("found results, exiting")
					return result
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)
			for asset in bundle.assets:
				result = handle_asset(asset)
				if result is not None:
					print("found resultss, exiting")
					return result


def handle_asset(asset):
	result = {}
	for id, obj in asset.objects.items():
		try:
			d = obj.read()
		except Exception as e:
			print("Could not read asset %s, %s" % (asset, e))
			continue
		# Not sure why, but if you don't do this you end up with read errors. Maybe the tree needs to be
		# fully traversed first so that references are resolved or something?
		output = yaml.dump(d)
		if isinstance(d, dict):
			# print("is dict! %s: %s" % (id, d))
			if "m_Name" in d and d["m_Name"] is not "":
				print("name %s" % d["m_Name"])
				if d["m_Name"] == "CARD_BACK":
					records = d["Records"]
					result = handle_records(records)
					return result
	return


def handle_records(records):
	result = []
	for record in records:
		print("handling record")
		result.append(handle_record(record))
	return result


def handle_record(record):
	result = {
		"id": record["m_ID"],
		"sortOrder": record["m_sortOrder"],
		"enabled": record["m_enabled"],
		"name": record["m_name"]["m_locValues"][0],
		"description": record["m_description"]["m_locValues"][0],
	}
	return result

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


if __name__ == "__main__":
	main()
