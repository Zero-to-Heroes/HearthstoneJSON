#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import UnityPy
from PIL import Image, ImageOps
from UnityPy.enums import ClassIDType

guid_to_path = {}


def main():
	p = ArgumentParser()
	p.add_argument("src")
	p.add_argument("--outdir", nargs="?", default="")
	p.add_argument("--skip-existing", action="store_true")
	p.add_argument(
		"--formats", nargs="*", default=["jpg", "png", "webp"],
		help="Which image formats to generate"
	)
	p.add_argument("--skip-tiles", action="store_true", help="Skip tiles generation")
	p.add_argument("--skip-thumbnails", action="store_true", help="Skip thumbnail generation")
	p.add_argument(
		"--only", type=str, nargs="?", help="Extract specific CardIDs (case-insensitive)"
	)
	p.add_argument("--orig-dir", type=str, default="orig", help="Name of output for originals")
	p.add_argument("--tiles-dir", type=str, default="tiles", help="Name of output for tiles")
	p.add_argument("--traceback", action="store_true", help="Raise errors during conversion")
	p.add_argument("--json-only", action="store_true", help="Only write JSON cardinfo")
	args = p.parse_args(sys.argv[1:])
	generate_card_textures(args.src, args)


def generate_card_textures(src, args):
	# for root, dirs, files in os.walk(src):
	# 	for file_name in files:
	# 		# generate file_path
	# 		file_path = os.path.join(root, file_name)
	# 		# load that file via UnityPy.load
	# 		env = UnityPy.load(file_path)
	# 		populate_guid_to_path(env)

	cards, textures = extract_info(src)
	paths = [card["path"] for card in cards.values()]
	print("Found %i cards, %i textures including %i unique in use." % (
		len(cards), len(textures), len(set(paths))
	))

	thumb_sizes = (256, 512)

	for id, values in sorted(cards.items()):
		path = values["path"]

		try:
			do_texture(path, id, textures, values, thumb_sizes, args)
		except Exception as e:
			sys.stderr.write("ERROR on %r (%r): %s\n" % (path, id, e))
			raise


def populate_guid_to_path(env):
	for obj in env.objects:
		print("checking type %s %s " % (obj.type, obj.type == ClassIDType.AssetBundle))
		if obj.serialized_type.nodes:
			# save decoded data
			try:
				tree = obj.read_typetree()
				print("tree %s" % (json.dumps(tree)))
			except:
				print("could not read %s" % obj.type)
				continue
			if "m_assets" in tree:
				for asset_info in tree["m_assets"]:
					print("asset_info %s" % (json.dumps(asset_info)))
					continue
					guid = asset_info["guid"]
					path = asset_info["Path"]
					path = path.lower()
					if not path.startswith("final/"):
						path = "final/" + path
					if not path.startswith("final/assets"):
						print("not handling path in guid_to_path %s" % path)
						continue
					guid_to_path[guid] = path
		else:
			data = obj.read()
			print("data %s" % data.raw_data)



def extract_info(src):
	textures = {}
	cards = {}

	for root, dirs, files in os.walk(src):
		for file_name in files:
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			env = UnityPy.load(file_path)
			handle_asset(env, textures)

	for root, dirs, files in os.walk(src):
		for file_name in files:
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			env = UnityPy.load(file_path)
			handle_gameobject(env, cards)

	return cards, textures


def handle_asset(env, textures):
	for obj in env.objects:
		if obj.type == ClassIDType.AssetBundle:
			# print("assetbundle %s" % obj)
			data = obj.read()
			# print("data %s" % data)
			container = data.m_Container
			# print("container %s" % container)				
			for path, asset in container.items():
				# print("considering %s, %s" % (path, asset))
				# asset = obj["asset"]
				textures[path] = asset.asset


def handle_gameobject(asset, cards):
	for obj in asset.objects:
		if obj.type == ClassIDType.GameObject:

			data = obj.read()
			cardid = data.name

			# if cardid != "CS1_042":
			# 	continue

			print("cardid: %s" % cardid)
			# print("d %s" % data)
			# print("components %s" % data.m_Components)
			if len(data.m_Components) < 2:
				continue

			monoBehavior = data.m_Components[1]
			# print("monoBehavior %s" % monoBehavior)
			carddef = monoBehavior.read()


			# print("carddef %s" % carddef)
			# print(carddef.to_dict())

			path = carddef.get("m_PortraitTexturePath")
			if not path:
				# Sometimes there's multiple per cardid, we remove the ones without art
				continue

			if ":" in path:
				guid = path.split(":")[1]
				# print("guid %s" % guid)
				path = guid

			tile = carddef.get("m_DeckCardBarPortrait")
			# print("tile %s" % tile)
			if tile:
				tile = tile.read()
				# print("tile %s" % tile.to_dict())


			cards[cardid] = {
				"path": path.lower(),
				"tile": tile.get("m_SavedProperties") if tile else {},
			}
			# print("cards %s" % cards)


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
			tile.m_TexEnvs["_MainTex"].m_Offset.X,
			tile.m_TexEnvs["_MainTex"].m_Offset.Y,
			tile.m_TexEnvs["_MainTex"].m_Scale.X,
			tile.m_TexEnvs["_MainTex"].m_Scale.Y,
			tile.m_Floats.get("_OffsetX", 0.0),
			tile.m_Floats.get("_OffsetY", 0.0),
			tile.m_Floats.get("_Scale", 1.0),
			img.width
		)

	x, y, width, height = get_rect(*props)
	bar = ImageOps.flip(tiled).crop((x, y, x + width, y + height))
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
	print("pptr %s" % pptr)
	
	texture = pptr.read()
	print("texture %s" % texture)
	flipped = None

	filename, exists = get_filename(args.outdir, args.orig_dir, id, ext=".png")
	print("filename %s" % filename)

	if not (args.skip_existing and exists):
		print("-> %r" % (filename))
		flipped = ImageOps.scale(texture.image, 1).convert("RGB")
		flipped.save(filename)

	for format in args.formats:
		ext = "." + format

		if not args.skip_tiles:
			filename, exists = get_filename(args.outdir, args.tiles_dir, id, ext=ext)
			if not (args.skip_existing and exists):
				tile_texture = generate_tile_image(texture.image, values["tile"])
				print("-> %r" % (filename))
				tile_texture.save(filename)
				

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
					flipped = ImageOps.scale(texture.image, 1).convert("RGB")
				thumb_texture = flipped.resize((sz, sz))
				print("-> %r" % (filename))
				thumb_texture.save(filename)



if __name__ == "__main__":
	main()
