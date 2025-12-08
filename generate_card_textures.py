#!/usr/bin/env python
import json
import os
import sys
import faulthandler; faulthandler.enable()
import UnityPy
from argparse import ArgumentParser
from typing import List, cast, Dict, Optional

from PIL import Image, ImageOps, ImageDraw
from UnityPy import Environment
from UnityPy.enums import ClassIDType
from UnityPy.helpers import TypeTreeHelper
from UnityPy.classes import PPtr, GameObject, ComponentPair, Tuple, Component, MonoBehaviour, Material, UnityPropertySheet, AssetBundle

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

class CardTextureInfo:
	portrait_path: str
	tile_info: UnityPropertySheet
 
	def __init__(self, portrait_path: str, tile_info: UnityPropertySheet):
		self.portrait_path = portrait_path
		self.tile_info = tile_info

# ./generate_card_textures.py --outdir out_png_test --tiles-dir tiles --cards-list cards_list.txt /e/Games/Hearthstone/Data/Win
# ./generate_card_textures.py --outdir out_png --tiles-dir tiles --cards-list cards_list.txt /e/Games/Hearthstone_Event_1/Data/Win
def main():
	TypeTreeHelper.read_typetree_c = False

	p = ArgumentParser()
	p.add_argument("src")
	p.add_argument("--outdir", nargs="?", default="out")
	p.add_argument("--skip-existing", action="store_true")
	p.add_argument("--orig-dir", type=str, default="orig", help="Name of output for originals")
	p.add_argument("--tiles-dir", type=str, default="tiles", help="Name of output for tiles")
	p.add_argument("--cards-list", type=str, help="Path to file with the list of cards to include")
	# p.add_argument(
	# 	"--formats", nargs="*", default=["png", "jpg"],
	# 	help="Which image formats to generate"
	# )
	args = p.parse_args(sys.argv[1:])
	generate_card_textures(args.src, args)


def generate_card_textures(src, args): 
    # Build an array of cards from the cards-list argument, if present
	if args.cards_list:
		with open(args.cards_list, "r") as f:
			cards_list = [line.strip() for line in f.read().splitlines()]
			print("cards_list: %s" % len(cards_list))
	else:
		cards_list = None
    
	print("Loading environment")
	env: Environment = UnityPy.load(src)
	print("Building cards_map")
	cards_map = build_cards_map(env, cards_list)
	print("cards_map: %s" % len(cards_map))
	# json.dump(cards_map, sys.stdout, ensure_ascii = False, indent = 4)
	textures_map = build_textures_map(env)
	print("textures_map: %s" % len(textures_map))
	cards_info: Dict[str, CardTextureInfo] = build_cards_info(env, cards_map, cards_list)
	print("cards_info: %s" % len(cards_info))

	paths = [card.portrait_path for card in cards_info.values()]
	print("Found %i cards, %i textures including %i unique in use." % (
		len(cards_map), len(textures_map), len(set(paths))
	))

	thumb_sizes = (256, 512)
	for card_id, texture_info in cards_info.items():
		try:
			# print("processing %r (%r)" % (texture_info, card_id))
			do_texture(env, card_id, texture_info, textures_map, thumb_sizes, args)
		except Exception as e:
			sys.stderr.write("ERROR on %r (%r): %s\n" % (texture_info, card_id, e))
			raise

	print("Job's done")


def build_cards_map(env: Environment, cards_list: Optional[List[str]] = None) -> Dict[str, str]:
	for obj in env.objects:
		if obj.type == ClassIDType.MonoBehaviour:
			dataM: MonoBehaviour = cast(MonoBehaviour, obj.read())
			if dataM.m_Name == "cards_map":
				tree = dataM.map
				keys = tree.keys
				values = tree.values
				print("keys: %s" % len(keys))
				print("values: %s" % len(values))
				# Build a dictionary of key => prefabid
				cards_map = {}
				for cardid, value in zip(keys, values):
					if cards_list and cardid not in cards_list:
						# print("skipping build_cards_map %s" % cardid)
						continue
					# if "BG" not in cardid:
					# 	continue
					# Only keep the id of the prefab, which means what is after prefab:
					asset_id = value.split("prefab:")[1]
					cards_map[cardid] = asset_id
				return cards_map
	# Return empty dict if no cards_map found
	return {}
				
    
def build_textures_map(env: Environment) -> Dict[str, PPtr]:
	textures = {}
	for obj in env.objects:
		if obj.type == ClassIDType.AssetBundle:
			data = cast(AssetBundle, obj.read())
			container = data.m_Container
			for path, asset in container:
				textures[path] = asset.asset
	return textures


def is_valid_pointer(ptr) -> bool:
	"""Check if a pointer is valid (not None, not UnknownObject, and has non-zero path_id)"""
	if ptr is None:
		return False
	# Check if it's an UnknownObject (which doesn't have path_id)
	if not hasattr(ptr, 'path_id'):
		return False
	# Check if path_id is non-zero (0 means null/unset in Unity)
	return ptr.path_id != 0

def get_pointer_path_id(ptr) -> str:
	"""Safely get the path_id of a pointer, returning a string representation"""
	if ptr is None:
		return "None"
	if not hasattr(ptr, 'path_id'):
		return "UnknownObject"
	return str(ptr.path_id)

def build_cards_info(env: Environment, cards_map: Dict[str, str], cards_list: Optional[List[str]] = None):
	cards = {}
	current_card_idx = 0
	# Iterate over the cards map
	for cardid, prefabid in cards_map.items():
		if cards_list is not None and cardid not in cards_list:
			# print("skipping build_cards_info %s" % cardid)
			continue
		prefab_pptr = env.container[prefabid]
		print("card %s: %s" % (current_card_idx, cardid))
		current_card_idx += 1
		prefab = cast(GameObject, prefab_pptr.read())
		components = cast(List[ComponentPair], prefab.m_Component)
		# Find the component that is a monobehavior
		for component in components:
			# print("component: %s" % component)
			component_pptr = component.component
			# print("component_pptr: %s" % component_pptr)
			if component_pptr.type.name == "MonoBehaviour":
				card_def = component_pptr.read()
				# print("card_def: %s" % card_def)
				attrs = [attr for attr in dir(card_def) if not attr.startswith("__")]
				# print("card_def attributes:", attrs)
    
				# Sometimes there's multiple per cardid, we remove the ones without art
				if not hasattr(card_def, "m_PortraitTexturePath"):
					print("\tskipping %s, no m_PortraitTexturePath" % cardid)
					continue
				portrait_path = card_def.__getattribute__("m_PortraitTexturePath")
				if ":" in portrait_path:
					portrait_path = portrait_path.split(":")[1]
				if len(portrait_path) == 0:
					print("\tskipping %s, portrait_path is empty" % cardid)
					continue
				# print("portrait_path: %s" % portrait_path)
		
				# Check for m_DeckCardBarPortrait
				tile_ptr: PPtr = None
				if hasattr(card_def, "m_DeckCardBarPortrait"):
					tile_ptr = card_def.__getattribute__("m_DeckCardBarPortrait")
					path_id_val = get_pointer_path_id(tile_ptr)
					print("\tm_DeckCardBarPortrait: path_id=%s" % path_id_val)
				else:
					print("\tm_DeckCardBarPortrait: attribute not found")
				
				# Check for alternative portrait attributes as fallbacks
				fallback_attrs = ["m_CustomDeckPortrait", "m_DeckBoxPortrait", "m_DeckPickerPortrait"]
				fallback_found = False
				for attr_name in fallback_attrs:
					if hasattr(card_def, attr_name):
						fallback_ptr = card_def.__getattribute__(attr_name)
						if is_valid_pointer(fallback_ptr):
							path_id_val = get_pointer_path_id(fallback_ptr)
							print("\t%s: path_id=%s (available as fallback)" % (attr_name, path_id_val))
							if not is_valid_pointer(tile_ptr):
								tile_ptr = fallback_ptr
								fallback_found = True
								print("\tUsing %s as fallback" % attr_name)
								break
			
				tile: Material = None if not is_valid_pointer(tile_ptr) else tile_ptr.read()
				# print("tile: %s" % tile)
				tile_info = None if tile == None else tile.m_SavedProperties
				if tile_info is None:
					path_id_str = get_pointer_path_id(tile_ptr)
					print("\tWARNING: tile_info is None for %s (tile_ptr.path_id=%s)" % (
						cardid, path_id_str
					))
				else:
					print("\ttile_info: found")
				texture_info: CardTextureInfo = CardTextureInfo(
					portrait_path = portrait_path.lower(),
					tile_info = tile_info,
				)
				cards[cardid] = texture_info

	return cards


def do_texture(env: Environment, card_id: str, texture_info: CardTextureInfo, textures: Dict[str, PPtr], thumb_sizes, args):
	try:
		texture_pptr = textures[texture_info.portrait_path]	
		print("texture_pptr: %s" % texture_pptr)
		texture = texture_pptr.read()
		print("texture: %s" % texture)
		flipped = None
		filename, exists = get_filename(args.outdir, args.orig_dir, card_id, ext=".png")

		if not (args.skip_existing and exists):
			print("-> %r" % (filename))
			flipped = texture.image.copy().convert("RGB")
			flipped.save(filename)

		ext = ".png"
		filename, exists = get_filename(args.outdir, args.tiles_dir, card_id, ext=ext)
		if not (args.skip_existing and exists):
			# print("will build texture for %r" % (filename))
			if not texture.image:
				print("texture has no image %s" % card_id)
			use_secondary_value = "coin" in card_id.lower()
			tile_texture = generate_tile_image(env, texture.image, texture_info.tile_info, use_secondary_value)
			if not tile_texture:
				print("could not generate tile texture %s" % card_id)
				# Some hero skins have no tiles, but still have the thumb
			else:
				print("-> %r" % (filename))
				tile_texture.save(filename)

		ext = ".jpg"
		for sz in thumb_sizes:
			thumb_dir = "%ix" % (sz)
			filename, exists = get_filename(args.outdir, thumb_dir, card_id, ext=ext)
			if not (args.skip_existing and exists):
				if not flipped:
					flipped = texture.image.copy().convert("RGB")
				thumb_texture = flipped.resize((sz, sz))
				print("-> %r" % (filename))
				thumb_texture.save(filename)
	except Exception as e:
		print("ERROR on %r (%r): %s" % (texture_info, card_id, e))
        


def generate_tile_image(env: Environment, img, tile_info, use_secondary_value):
	print("tile: %s" % tile_info)    
	if (img.width, img.height) != (512, 512):
		img = img.resize((512, 512), Image.ANTIALIAS)
  
	# tile the image horizontally (x2 is enough),
	# some cards need to wrap around to create a bar (e.g. Muster for Battle),
	# also discard alpha channel (e.g. Soulfire, Mortal Coil)
	tiled = Image.new("RGB", (img.width * 2, img.height))
	tiled.paste(img, (0, 0))
	tiled.paste(img, (img.width, 0))
 
	# Default props
	offset_x = 0.0
	offset_y = 0.0
	scale_x = 1.0
	scale_y = 1.0
	extra_offset_x = 0.0
	extra_offset_y = 0.0
	extra_scale = 1.0
 
	if tile_info is not None:		
		main_tex = None
		for entry in tile_info.m_TexEnvs:
			if isinstance(entry, tuple) and entry[0] == "_MainTex":
				main_tex = entry[1]
				print("found main_tex: %s" % main_tex)
				break
		if main_tex is None:
			print("No _MainTex found in m_TexEnvs")
			return None
		print("main_tex: %s" % main_tex)
		offset_x = main_tex.m_Offset.x
		offset_y = main_tex.m_Offset.y
		scale_x = main_tex.m_Scale.x
		scale_y = main_tex.m_Scale.y
		extra_offset_x = get_float(tile_info.m_Floats, "_OffsetX", 0.0)
		extra_offset_y = get_float(tile_info.m_Floats, "_OffsetY", 0.0)
		extra_scale   = get_float(tile_info.m_Floats, "_Scale", 1.0)
  
		# Use get_rect to calculate the crop rectangle
		x, y, width, height = get_rect(
			offset_x, offset_y, scale_x, scale_y,
			extra_offset_x, extra_offset_y, extra_scale,
			img.width
		)
	# Hardcode the value (taken from the Counterfeit coin)
	elif use_secondary_value:
		x = 467
		y = 223
		width = 440
		height = 101
		print("rect secondary: x=%d, y=%d, width=%d, height=%d" % (x, y, width, height))
  	# For BG
	else:
		x = 0
		y = 300
		width = 512
		height = 117
		print("rect: x=%d, y=%d, width=%d, height=%d" % (x, y, width, height))

	# Clamp to image bounds
	x = max(0, min(x, img.width * 2 - 1))
	y = max(0, min(y, img.height - 1))
	width = max(1, min(width, img.width * 2 - x))
	height = max(1, min(height, img.height - y))

	# Invert Y for PIL (since Unity's 0 is bottom, PIL's 0 is top)
	y = img.height - y - height

	bar = tiled.crop((x, y, x + width, y + height))

	# Flip if negative scale
	if scale_x * extra_scale < 0:
		bar = ImageOps.mirror(bar)
	if scale_y * extra_scale < 0:
		bar = ImageOps.flip(bar)

	# Make white background transparent
	bar = bar.convert("RGBA")
	bar = make_white_bg_transparent(bar)
	# print("made white bg transparent")
 
	# Remove the leftmost 55 pixels
	bar = bar.crop((55, 0, bar.width, bar.height))
 

	return bar.resize((OUT_WIDTH, OUT_HEIGHT), Image.LANCZOS)

 
def make_white_bg_transparent(img, threshold=240):
    img = img.convert("RGBA")
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    pixels = img.load()
    mask_pixels = mask.load()

    # Helper to check if a pixel is "white enough"
    def is_white(px):
        return px[0] >= threshold and px[1] >= threshold and px[2] >= threshold

    # Flood fill from all white border pixels
    from collections import deque
    queue = deque()

    # Add all white border pixels to the queue
    for x in range(w):
        if is_white(pixels[x, 0]):
            queue.append((x, 0))
        if is_white(pixels[x, h-1]):
            queue.append((x, h-1))
    for y in range(h):
        if is_white(pixels[0, y]):
            queue.append((0, y))
        if is_white(pixels[w-1, y]):
            queue.append((w-1, y))

    # Directions: up, down, left, right
    directions = [(-1,0), (1,0), (0,-1), (0,1)]

    # Flood fill
    while queue:
        x, y = queue.popleft()
        if 0 <= x < w and 0 <= y < h and mask_pixels[x, y] == 0 and is_white(pixels[x, y]):
            mask_pixels[x, y] = 255
            for dx, dy in directions:
                queue.append((x+dx, y+dy))

    # Apply mask: set alpha to 0 where mask is 255
    new_pixels = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if mask_pixels[x, y] == 255:
                new_pixels.append((r, g, b, 0))
            else:
                new_pixels.append((r, g, b, a))
    img.putdata(new_pixels)
    return img


def get_float(m_Floats, key, default=0.0):
    for k, v in m_Floats:
        if k == key:
            return v
    return default


# Deck tile generation
TEX_COORDS = [(0.0, 0.3856), (1.0, 0.6144)]
OUT_DIM = 256
OUT_WIDTH = round(TEX_COORDS[1][0] * OUT_DIM - TEX_COORDS[0][0] * OUT_DIM)
OUT_HEIGHT = round(TEX_COORDS[1][1] * OUT_DIM - TEX_COORDS[0][1] * OUT_DIM)

def get_rect(ux, uy, usx, usy, sx, sy, ss, tex_dim=512):
    """
    Calculate the crop rectangle for the deck bar image, converting Unity UV/material properties
    to pixel coordinates for cropping in PIL.

    Parameters:
    - ux, uy: Main texture UV offset (UnityTexEnv.m_Offset.x/y)
    - usx, usy: Main texture UV scale (UnityTexEnv.m_Scale.x/y)
    - sx, sy: Extra offset floats (_OffsetX, _OffsetY)
    - ss: Extra scale float (_Scale)
    - tex_dim: Texture dimension (default 512)

    Returns:
    - (x, y, width, height): Rectangle in pixel coordinates
    """

    # Calculate UV coordinates for top-left and bottom-right corners
    tl_u = ((TEX_COORDS[0][0] + sx) * ss) * usx + ux
    tl_v = ((TEX_COORDS[0][1] + sy) * ss) * usy + uy
    br_u = ((TEX_COORDS[1][0] + sx) * ss) * usx + ux
    br_v = ((TEX_COORDS[1][1] + sy) * ss) * usy + uy

    # Handle horizontal crossover (if needed)
    horiz_delta = tl_u - br_u
    if horiz_delta > 0:
        tl_u -= horiz_delta
        br_u += horiz_delta

    # Convert UVs to pixel coordinates
    x = round(tl_u * tex_dim)
    y = round(tl_v * tex_dim)
    width = round(abs((br_u - tl_u) * tex_dim))
    height = round(abs((br_v - tl_v) * tex_dim))

    # Adjust x and y for wrap-around/tiling
    x = (x + width) % tex_dim - width
    y = (y + height) % tex_dim - height

    # Ensure minimum visible area
    min_visible = tex_dim // 4
    while x + width < min_visible:
        x += tex_dim
    while y + height < 0:
        y += tex_dim

    # Final wrap for negative x
    if x < 0:
        x += tex_dim

    return (x, y, width, height)


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



if __name__ == "__main__":
	main()
