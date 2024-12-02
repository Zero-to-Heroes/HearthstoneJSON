#!/usr/bin/env python
import json
import os
import sys
from argparse import ArgumentParser

import UnityPy
from PIL import Image, ImageOps
from UnityPy import Environment
from UnityPy.enums import ClassIDType
import faulthandler; faulthandler.enable()
from UnityPy.helpers import TypeTreeHelper
from UnityPy.classes import PPtr

class Logger(object):
    def __init__(self, logFile):
        self.terminal = sys.stdout
        self.log = open(logFile, "w")
   
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass    

sys.stdout = Logger("generate_card_textures.log")

# ./generate_audio.py /e/t > out.txt
def main():
	p = ArgumentParser()
	p.add_argument("src")
	args = p.parse_args(sys.argv[1:])

	sound_effects = extract_info(args.src)
	with open('./ref/sound_effects.json', 'w') as resultFile:
		resultFile.write(json.dumps(sound_effects))

def main():
	TypeTreeHelper.read_typetree_c = False

	p = ArgumentParser()
	p.add_argument("src")
	p.add_argument("--outdir", nargs="?", default="out")
	p.add_argument("--skip-existing", action="store_true")
	p.add_argument("--orig-dir", type=str, default="orig", help="Name of output for originals")
	p.add_argument("--tiles-dir", type=str, default="tiles", help="Name of output for tiles")
	p.add_argument(
		"--formats", nargs="*", default=["jpg"],
		help="Which image formats to generate"
	)
	args = p.parse_args(sys.argv[1:])
	generate_card_textures(args.src, args)


def generate_card_textures(src, args):
	for root, dirs, files in os.walk(src):
		for file_name in files:
			print(f"file_name: {file_name}")
			# generate file_path
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			try:
				env = UnityPy.load(file_path)
				for path,obj in env.container.items():
					# if obj.type.name in ["Texture2D"]:
					# data = obj.read()
					# create dest based on original path
					dest = os.path.join("", *path.split("/"))
					# correct extension
					dest, ext = os.path.splitext(dest)
					dest = dest + ".png"
					# print(f"\tdest: {dest}, path: {path}, path_id: {obj.path_id}")
			except Exception as e:
				print(f"ERROR: {e}")
				continue

	cards, textures, env = extract_info(src)
	paths = [card["path"] for card in cards.values()]
	print("Found %i cards, %i textures including %i unique in use." % (
		len(cards), len(textures), len(set(paths))
	))

	thumb_sizes = (256, 512)
	for id, values in sorted(cards.items()):
		path = values["path"]
		try:
			do_texture(env, path, id, textures, values, thumb_sizes, args)
		except Exception as e:
			sys.stderr.write("ERROR on %r (%r): %s\n" % (path, id, e))
			raise


def extract_info(src):
	textures = {}
	cards = {}

	# env = UnityPy.load(src)
	for root, dirs, files in os.walk(src):
		for file_name in files:
			print("Generating card textures from %r" % (file_name))
			file_path = os.path.join(root, file_name)
			# load that file via UnityPy.load
			try:
				env = UnityPy.load(file_path)
				# for path,obj in env.container.items():
				# 	if obj.type.name in ["Texture2D"]:						
				# 		# data = obj.read()
				# 		# create dest based on original path
				# 		dest = os.path.join("", *path.split("/"))
				# 		# correct extension
				# 		dest, ext = os.path.splitext(dest)
				# 		dest = dest + ".png"
				# 		# print(f"dest: {dest}, path: {path}, path_id: {obj.path_id}")
				handle_asset(env, textures)
				handle_gameobject(env, cards)
			except Exception as e:
				print(f"ERROR: {e}")
				continue

	return cards, textures, env


def handle_asset(env, textures):
	for obj in env.objects:
		if obj.type == ClassIDType.AssetBundle:
			data = obj.read()
			container = data.m_Container
			for path, asset in container.items():
				textures[path] = asset.asset


def handle_gameobject(asset: Environment, cards):
	for obj in asset.objects:
		# continue
		cardid = ''
		# try:
		if obj.type == ClassIDType.GameObject:
			data = obj.read()	
			cardid = data.name

			# if cardid != "TTN_469" and cardid != "TTN_078":
			# 	continue

			# json.dump(data, sys.stdout, ensure_ascii = False, indent = 4)
			# print("cardid: %s" % cardid)
			if len(data.m_Components) < 2:
				continue

			carddef = data.m_Components[1].read()
			# print("carddef.type %s" % (type(carddef).__name__))
			if type(carddef).__name__ == "NodeHelper":
				# print("skipping %s" % (cardid))
				continue

			path = carddef.get("m_PortraitTexturePath")
			if not path:
				# Sometimes there's multiple per cardid, we remove the ones without art
				continue

			if ":" in path:
				guid = path.split(":")[1]
				path = guid

			print("carddef: %s" % carddef)
			tile = carddef.get("m_DeckCardBarPortrait")
			print("tile prop: %s" % tile)
			if tile:
				tile = tile.read()
				if not tile:
					raise TypeError("could not read tile")
			# else:
			# 	raise TypeError("stopping")


			# print("tile obj: %s" % tile)
			# print("building tile for %s" % cardid)
			# json.dump(tile, sys.stdout, ensure_ascii = False, indent = 4)
			tileInfo = {}
			try:
				tileInfo = tile.get("m_SavedProperties")
			except:
				print("could not get tileInfo for %s" % cardid)

			cards[cardid] = {
				"path": path.lower(),
				"tile": tileInfo,
			}
			# print("built tile for %s" % cards[cardid])
			# m_tex: PPtr = cards[cardid]['tile'].m_TexEnvs[''].m_Texture
			# print(f"search file name: {os.path.basename(m_tex.external_name.lower())}, from {m_tex.assets_file}")
			# file = m_tex.assets_file.environment.cabs.get(m_tex.external_name.lower())
			# print(f"m_tex: file_id: {m_tex.file_id}, assets_file: {m_tex.assets_file}, path_id: {m_tex.path_id}, type: {m_tex.type}, external_name: {m_tex.external_name}, index: {m_tex.index}, dict: {m_tex.__dict__}")
			# print("m_Texture: %s" % m_tex)
			# print(f"found file: {file}")
			# build a list of all the objects contained in the cab file
			# objects: dict = {}
			# for cab in asset.cabs.values():
			# 	# print(f"cab: {cab}")
			# 	try:
			# 		cabObjects: dict = cab.objects
			# 		objects.update(cabObjects)
			# 	except:
			# 		continue
			# cabFile = asset.cabs.get(m_tex.external_name.lower())
			# print(f"found cabFile: {cabFile}")
			# # print(f"found cabFile.objects: {cabFile.objects}, {m_tex.path_id}")
			# # print(f"all objects: {objects}")
			# obj = cabFile.objects[m_tex.path_id]
			# print(f"found obj: {obj}")
			# read = obj.read()
			# print(f"found read: {read}")
		# except Exception as e:
		# 	with open("error_asset", "wb") as f:
		# 		f.write(obj.assets_file.save())
		# 	print(f"ERROR for {cardid}")
		# 	print(e)


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


def generate_tile_image(env: Environment, img, tile):
	if (img.width, img.height) != (512, 512):
		img = img.resize((512, 512), Image.ANTIALIAS)

	# tile the image horizontally (x2 is enough),
	# some cards need to wrap around to create a bar (e.g. Muster for Battle),
	# also discard alpha channel (e.g. Soulfire, Mortal Coil)
	tiled = Image.new("RGB", (img.width * 2, img.height))
	tiled.paste(img, (0, 0))
	tiled.paste(img, (img.width, 0))

	print("tile: %s" % tile)
	# props = (-0.13, 0.13, 1, 1, 0, 0, 1.1, img.width)
	props = (-0.2, 0.25, 1, 1, 0, 0, 1, img.width)
	# TODO: fix this
	# if tile:
	# 	print("texEnvs: %s" % tile.m_TexEnvs)
	# 	print("texEnvs 2: %s" % tile.m_TexEnvs[''])
	# 	texEnvs = tile.m_TexEnvs['']
	# 	m_Texture: PPtr = texEnvs.m_Texture
	# 	tex = m_Texture.read()
	# 	print("m_Texture: %s" % m_Texture)
	# 	m_Offset = texEnvs.m_Offset
	# 	print("m_Offset: %s" % m_Offset)
	# 	m_Scale = texEnvs.m_Scale
	# 	print("m_Scale: %s" % m_Scale)
	# 	m_Floats = tile.m_Floats
	# 	print("m_Floats: %s" % m_Floats)
	# 	print("tex: %s" % tex)
	# 	props = (
	# 		tile.m_TexEnvs["_MainTex"].m_Offset.X,
	# 		tile.m_TexEnvs["_MainTex"].m_Offset.Y,
	# 		tile.m_TexEnvs["_MainTex"].m_Scale.X,
	# 		tile.m_TexEnvs["_MainTex"].m_Scale.Y,
	# 		tile.m_Floats.get("_OffsetX", 0.0),
	# 		tile.m_Floats.get("_OffsetY", 0.0),
	# 		tile.m_Floats.get("_Scale", 1.0),
	# 		img.width
	# 	)
		# print("tile props: %s" % (props,))

	x, y, width, height = get_rect(*props)
	# print("x: %s, y: %s, width: %s, height: %s" % (x, y, width, height))
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


def do_texture(env: Environment, path, id, textures, values, thumb_sizes, args):
	if not path:
		return

	if path not in textures:
		return

	pptr = textures[path]
	
	texture = pptr.read()
	flipped = None

	filename, exists = get_filename(args.outdir, args.orig_dir, id, ext=".png")

	if not (args.skip_existing and exists):
		print("-> %r" % (filename))
		flipped = ImageOps.scale(texture.image, 1).convert("RGB")
		flipped.save(filename)

	for format in args.formats:
		ext = "." + format
		filename, exists = get_filename(args.outdir, args.tiles_dir, id, ext=ext)
		if not (args.skip_existing and exists):
			print("will build texture for %r" % (filename))
			tile_texture = generate_tile_image(env, texture.image, values["tile"])
			print("-> %r" % (filename))
			tile_texture.save(filename)
				

		if ext == ".png":
			# skip png generation for thumbnails
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
