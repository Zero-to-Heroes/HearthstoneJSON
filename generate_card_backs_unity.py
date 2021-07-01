#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import unitypack
import yaml
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment
from unitypack.object import ObjectPointer

cardBacks = []
assets = {}
guid_to_path = {}

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

	build_card_backs(args.files)

	with open('./ref/card_backs_unity.json', 'w') as resultFile:
		result = {
			"cardBacks": cardBacks
		}
		resultFile.write(json.dumps(result))


def build_card_backs(files):
	env = UnityEnvironment()

	for file in files:
		# print("\tloading %s" % file)
		f = open(file, "rb")
		env.load(f)

	for bundle in env.bundles.values():
		# print("\tbundle asset %s" % bundle.path)
		# if "sound" in bundle.path:
		for asset in bundle.assets:
			handle_asset_load(asset)


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
		
		d = obj.read()
		# Not sure why, but if you don't do this you end up with read errors. Maybe the tree needs to be
		# fully traversed first so that references are resolved or something?
		# output = yaml.dump(d)
		if isinstance(d, dict):
			# print("is dict! %s: %s" % (id, d))
			if "m_Name" in d and d["m_Name"] is not "":
				if d["m_Name"] == "CARD_BACK":
					records = d["Records"]
					handle_records(records)


def handle_records(records):
	for record in records:
		handle_record(record)


def handle_record(record):
	if record["m_ID"] != 5:
		return

	# print("handling record")
	# print(yaml.dump(record))
	prefabName = record["m_prefabName"]
	# print("prefabName %s" % (prefabName))
	if ":" in prefabName:
		guid = prefabName.split(":")[1]
		# print("guid %s" % (guid))
		if guid in assets:
			# print("guid %s" % (guid))
			prefab = assets[guid]
			# print("prefab %s" % (prefab))
			resolved = prefab.resolve()
			# print("prefab dump")
			# print(yaml.dump(resolved))
			# dump(resolved, 1)

			print("\n\nid: %s" % record["m_ID"])

			script = resolved.component[1]["component"].resolve()
			print("script")
			print(yaml.dump(script))

			gameobject = script["m_GameObject"].resolve()
			print("\n\ngameobject: %s" % gameobject.name)
			print(yaml.dump(gameobject))

			print(yaml.dump(gameobject.component[0]["component"].resolve()))
			print(yaml.dump(gameobject.component[1]["component"].resolve()))

			mesh = script["m_CardBackMesh"].resolve()

			# print(yaml.dump(mesh))
			# dump(mesh, 1)
			print("Mesh: %s" % mesh.name)

			material = script["m_CardBackMaterial"].resolve()
			print("\n\nmaterial: %s" % material.name)
			print(yaml.dump(material))
			dump(material, 1)

			shader = material.shader.resolve()
			props = shader.__dict__["_obj"]["m_ParsedForm"]
			shaderName = props["m_Name"].replace("/", "_")
			print("\n\nshader: %s" % shaderName)

			print(yaml.dump(shader))
			dump(shader, 1)
			print("props %s" % props)
			print("name2 %s" % props["m_Name"])
			
			# Could this be used for the animated version?
			# try:
			# 	material = script["m_CardBackMaterial1"].resolve()
			# 	print("material1: %s" % material.name)
			# 	print(yaml.dump(material))
			# except:
			# 	a = 1

			texture = script["m_CardBackTexture"].resolve()
			# print(yaml.dump(texture))
			# dump(texture, 1)
			print("\n\ntexture: %s" % texture.name)
			
			result = {
				"id": record["m_ID"],
				"mesh": mesh.name,
				"texture": texture.name,
				"shader": shaderName,
			}
			cardBacks.append(result)
			# raise ValueError("the end")



def handle_asset_load(asset):
	for obj in asset.objects.values():
		if obj.type == "AssetBundle":
			d = obj.read()
			for guid, obj in d["m_Container"]:
				guid = guid.lower()
				asset = obj["asset"]
				# print("guid %s" % guid)
				assets[guid] = asset


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
		try:
			print("\t" * level, "obj.%s = %r" % (attr, getattr(obj, attr)))
		except:
			a = 1

if __name__ == "__main__":
	main()
