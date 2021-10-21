#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser
from collections import OrderedDict

import unitypack
from PIL import Image, ImageOps
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment
from unitypack.object import ObjectPointer
from unitypack.utils import extract_audioclip_samples

guid_to_path = {}


def main():
	p = ArgumentParser()
	p.add_argument("--outdir", nargs="?", default="")
	p.add_argument("--skip-existing", action="store_true")
	p.add_argument(
		"--formats", nargs="*", default=["jpg", "png", "webp"],
		help="Which image formats to generate"
	)
	p.add_argument("--skip-tiles", action="store_true", help="Skip tiles generation")
	p.add_argument("--skip-coins", action="store_true", help="Skip coins generation")
	p.add_argument("--skip-thumbnails", action="store_true", help="Skip thumbnail generation")
	p.add_argument(
		"--only", type=str, nargs="?", help="Extract specific CardIDs (case-insensitive)"
	)
	p.add_argument("--orig-dir", type=str, default="orig", help="Name of output for originals")
	p.add_argument("--tiles-dir", type=str, default="tiles", help="Name of output for tiles")
	p.add_argument("--coins-dir", type=str, default="coins", help="Name of output for coins")
	p.add_argument("--traceback", action="store_true", help="Raise errors during conversion")
	p.add_argument("--json-only", action="store_true", help="Only write JSON cardinfo")
	p.add_argument("files", nargs="+")
	args = p.parse_args(sys.argv[1:])

	for file in args.files:
		if file.endswith(".assets") or file.endswith(".asset"):
			with open(file, "rb") as f:
				asset = Asset.from_file(f)
				populate_guid_to_path(asset)
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)
			for asset in bundle.assets:
				populate_guid_to_path(asset)

	filter_ids = args.only.lower().split(",") if args.only else []

	cards, textures = extract_info(args.files, filter_ids)
	paths = [card["path"] for card in cards.values()]
	print("Found %i cards, %i textures including %i unique in use." % (
		len(cards), len(textures), len(set(paths))
	))

	thumb_sizes = (256, 512)

	for id, values in sorted(cards.items()):
		if filter_ids and id.lower() not in filter_ids:
			continue
		path = values["path"]

		if args.json_only:
			tile = values["tile"]
			d = {
				"Name": id,
				"PortraitPath": path,
			}
			if tile:
				d["DcbTexScaleX"] = tile["m_TexEnvs"]["_MainTex"]["m_Scale"]["x"]
				d["DcbTexScaleY"] = tile["m_TexEnvs"]["_MainTex"]["m_Scale"]["y"]
				d["DcbTexOffsetX"] = tile["m_TexEnvs"]["_MainTex"]["m_Offset"]["x"]
				d["DcbTexOffsetY"] = tile["m_TexEnvs"]["_MainTex"]["m_Offset"]["y"]
				d["DcbShaderScale"] = tile["m_Floats"].get("_Scale", 1.0)
				d["DcbShaderOffsetX"] = tile["m_Floats"].get("_OffsetX", 0.0)
				d["DcbShaderOffsetY"] = tile["m_Floats"].get("_OffsetY", 0.0)
			with open(id + ".json", "w") as f:
				json.dump(d, f)
			continue

		try:
			do_texture(path, id, textures, values, thumb_sizes, args)
		except Exception as e:
			sys.stderr.write("ERROR on %r (%r): %s (Use --traceback for details)\n" % (path, id, e))
			if args.traceback:
				raise


def populate_guid_to_path(asset):
	for id, obj in asset.objects.items():
		try:
			d = obj.read()
			for asset_info in d["m_assets"]:
				guid = asset_info["Guid"]
				path = asset_info["Path"]
				path = path.lower()
				if not path.startswith("final/"):
					path = "final/" + path
				if not path.startswith("final/assets"):
					print("not handling path in guid_to_path %s" % path)
					continue
				guid_to_path[guid] = path
		except:
			continue


def extract_info(files, filter_ids):
	textures = {}
	cards = {}
	env = UnityEnvironment()

	for file in files:
		f = open(file, "rb")
		env.load(f)

	for bundle in env.bundles.values():
		for asset in bundle.assets:
			handle_asset(asset, textures, cards, filter_ids)

	for bundle in env.bundles.values():
		for asset in bundle.assets:
			handle_gameobject(asset, textures, cards, filter_ids)

	return cards, textures


def handle_asset(asset, textures, cards, filter_ids):
	for obj in asset.objects.values():
		if obj.type == "AssetBundle":
			d = obj.read()
			for path, obj in d["m_Container"]:
				asset = obj["asset"]
				textures[path] = asset


def handle_gameobject(asset, textures, cards, filter_ids):
	for obj in asset.objects.values():
		if obj.type == "GameObject":
			d = obj.read()
			cardid = d.name

			if filter_ids and cardid.lower() not in filter_ids:
				continue
			if cardid in ("CardDefTemplate", "HiddenCard"):
				# not a real card
				cards[cardid] = {"path": "", "tile": ""}
				continue
			if len(d.component) < 2:
				# Not a CardDef
				continue
			script = d.component[1]
			if isinstance(script, dict):  # Unity 5.6+
				carddef = script["component"].resolve()
			else:  # Unity <= 5.4
				carddef = script[1].resolve()

			if not isinstance(carddef, dict) or "m_PortraitTexturePath" not in carddef:
				# Not a CardDef
				continue

			path = carddef["m_PortraitTexturePath"]
			if not path:
				# Sometimes there's multiple per cardid, we remove the ones without art
				continue

			if ":" in path:
				guid = path.split(":")[1]
				if guid in guid_to_path:
					path = guid_to_path[guid]
				else:
					path = guid
					if guid == "6893f0e0abdd51d4888a2035ea78055f":
						print("WARN: Could not find %s in handle_gameobject (path=%s)" % (guid, path))

			tile = carddef.get("m_DeckCardBarPortrait")
			if tile:
				tile = tile.resolve()

			mercenary_coin = carddef.get("m_MercenaryCoinPortrait")
			if mercenary_coin:
				mercenary_coin = mercenary_coin.resolve()


			cards[cardid] = {
				"path": path.lower(),
				"tile": tile.saved_properties if tile else {},
				"mercenary_coin": mercenary_coin.saved_properties if mercenary_coin else {},
			}


# Deck tile generation
TEX_COORDS = [(0.0, 0.3856), (1.0, 0.6144)]
OUT_DIM = 256
OUT_WIDTH = round(TEX_COORDS[1][0] * OUT_DIM - TEX_COORDS[0][0] * OUT_DIM)
OUT_HEIGHT = round(TEX_COORDS[1][1] * OUT_DIM - TEX_COORDS[0][1] * OUT_DIM)


def get_rect(ux, uy, usx, usy, sx, sy, ss, tex_dim=512):
	# calc the coords
	tl_x = ((TEX_COORDS[0][0] + sx) * ss) * usx + ux
	tl_y = ((TEX_COORDS[0][1] + sy) * ss) * usy + uy
	br_x = ((TEX_COORDS[1][0] + sx) * ss) * usx + ux
	br_y = ((TEX_COORDS[1][1] + sy) * ss) * usy + uy

	# adjust if x coords cross-over
	horiz_delta = tl_x - br_x
	if horiz_delta > 0:
		tl_x -= horiz_delta
		br_x += horiz_delta

	# get the bar rectangle at tex_dim size
	x = round(tl_x * tex_dim)
	y = round(tl_y * tex_dim)
	width = round(abs((br_x - tl_x) * tex_dim))
	height = round(abs((br_y - tl_y) * tex_dim))

	# adjust x and y, so that texture is "visible"
	x = (x + width) % tex_dim - width
	y = (y + height) % tex_dim - height

	# ??? to cater for some special cases
	min_visible = tex_dim / 4
	while x + width < min_visible:
		x += tex_dim
	while y + height < 0:
		y += tex_dim

	# ensure wrap around is used
	if x < 0:
		x += tex_dim

	return (x, y, width, height)


def generate_tile_image(img, tile):
	if (img.width, img.height) != (512, 512):
		img = img.resize((512, 512), Image.ANTIALIAS)

	# tile the image horizontally (x2 is enough),
	# some cards need to wrap around to create a bar (e.g. Muster for Battle),
	# also discard alpha channel (e.g. Soulfire, Mortal Coil)
	tiled = Image.new("RGB", (img.width * 2, img.height))
	tiled.paste(img, (0, 0))
	tiled.paste(img, (img.width, 0))

	props = (-0.2, 0.25, 1, 1, 0, 0, 1, img.width)
	if tile:
		props = (
			tile["m_TexEnvs"]["_MainTex"]["m_Offset"]["x"],
			tile["m_TexEnvs"]["_MainTex"]["m_Offset"]["y"],
			tile["m_TexEnvs"]["_MainTex"]["m_Scale"]["x"],
			tile["m_TexEnvs"]["_MainTex"]["m_Scale"]["y"],
			tile["m_Floats"].get("_OffsetX", 0.0),
			tile["m_Floats"].get("_OffsetY", 0.0),
			tile["m_Floats"].get("_Scale", 1.0),
		)

	x, y, width, height = get_rect(*props)

	bar = tiled.crop((x, y, x + width, y + height))
	bar = ImageOps.flip(bar)
	# negative x scale means horizontal flip
	if props[2] < 0:
		bar = ImageOps.mirror(bar)

	return bar.resize((OUT_WIDTH, OUT_HEIGHT), Image.LANCZOS)


def generate_coin_image(img, coin, filename):
	if not coin:
		print("\tno coin for image")
		return

	print("handling coin %s: %s" % (filename, coin))
	if (img.width, img.height) != (512, 512):
		img = img.resize((512, 512), Image.ANTIALIAS)
		
	rgbImage = Image.new("RGB", (img.width, img.height))

	# props = (-0.2, 0.25, 1, 1, 0, 0, 1, img.width)
	if coin:
		props = (
			coin["m_TexEnvs"]["_MainTex"]["m_Offset"]["x"],
			coin["m_TexEnvs"]["_MainTex"]["m_Offset"]["y"],
			coin["m_TexEnvs"]["_MainTex"]["m_Scale"]["x"],
			coin["m_TexEnvs"]["_MainTex"]["m_Scale"]["y"],
			coin["m_Floats"].get("_OffsetX", 0.0),
			coin["m_Floats"].get("_OffsetY", 0.0),
			coin["m_Floats"].get("_Scale", 1.0),
		)
		# print("props %s" % props)

	x, y, width, height = get_rect(*props)

	bar = rgbImage.crop((x, y, x + width, y + height))
	bar = ImageOps.flip(bar)
	# negative x scale means horizontal flip
	if props[2] < 0:
		bar = ImageOps.mirror(bar)

	return bar.resize((OUT_WIDTH, OUT_HEIGHT), Image.LANCZOS)


def get_dir(basedir, dirname):
	ret = os.path.join(basedir, dirname)
	if not os.path.exists(ret):
		os.makedirs(ret)
	return ret


def get_filename(basedir, dirname, name, ext=".png"):
	dirname = get_dir(basedir, dirname)
	filename = name + ext
	path = os.path.join(dirname, filename)
	return path, os.path.exists(path)


def do_texture(path, id, textures, values, thumb_sizes, args):
	if not path:
		return

	if path not in textures:
		return

	pptr = textures[path]
	texture = pptr.resolve()
	flipped = None

	filename, exists = get_filename(args.outdir, args.orig_dir, id, ext=".png")
	if not "SWL" in filename:
		return
	
	if not (args.skip_existing and exists):
		print("-> %r" % (filename))
		flipped = ImageOps.flip(texture.image).convert("RGB")
		flipped.save(filename)

	for format in args.formats:
		ext = "." + format

		# if not args.skip_tiles:
		# 	filename, exists = get_filename(args.outdir, args.tiles_dir, id, ext=ext)
		# 	if not (args.skip_existing and exists):
		# 		tile_texture = generate_tile_image(texture.image, values["tile"])
		# 		print("-> %r" % (filename))
		# 		tile_texture.save(filename)
				
		# if not args.skip_coin:
		filename, exists = get_filename(args.outdir, args.coins_dir, id, ext=ext)
		if not (args.skip_existing and exists):
			print("-> %r" % (filename))
			coin = generate_coin_image(texture.image, values["mercenary_coin"], filename)
			coin.save(filename)

		if ext == ".png":
			# skip png generation for thumbnails
			continue

		if args.skip_thumbnails:
			# --skip-thumbnails was specified
			continue

		for sz in thumb_sizes:
			thumb_dir = "%ix" % (sz)
			filename, exists = get_filename(args.outdir, thumb_dir, id, ext=ext)
			if not (args.skip_existing and exists):
				if not flipped:
					flipped = ImageOps.flip(texture.image).convert("RGB")
				thumb_texture = flipped.resize((sz, sz))
				print("-> %r" % (filename))
				thumb_texture.save(filename)



if __name__ == "__main__":
	main()
