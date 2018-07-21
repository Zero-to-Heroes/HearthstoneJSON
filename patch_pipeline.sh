#!/bin/bash

set -e

BASEDIR="$(readlink -f "$(dirname "$0")")"
BUILD="$1"

isnum='^[0-9]+$'
if ! [[ $BUILD =~ $isnum ]]; then
	>&2 echo "USAGE: $0 [BUILD]"
	exit 1
fi

# Base build directory from extract-scripts
BUILDDIR="$BASEDIR/build"

# Directory where processed CardDefs.xml go
PROCESSED_DIR="$BUILDDIR/processed/$BUILD"

# Git repositories
SUNWELL_GIT="$BUILDDIR/Sunwell"
HSFONTS_GIT="$BUILDDIR/hs-fonts.git"
HSCODE_GIT="$BASEDIR/hscode.git"
HSDATA_GIT="$BASEDIR/hsdata.git"
HSPROTO_GIT="$BASEDIR/hsproto.git"


# Base and output path for 'hsb' blte
NGDP_DIR="/mnt/home/ngdp"
NGDP_OUT="$NGDP_DIR/out"

# Directory storing the build data files
HS_RAW_BUILDDIR="/mnt/home/data/ngdp/hsb/$BUILD"

# Directory that contains card textures
CARDARTDIR="$BUILDDIR/card-art"

# HearthstoneJSON file generator
HEARTHSTONEJSON_BIN="$BASEDIR/generate_hearthstonejson.sh"

# HearthstoneJSON generated files directory
HSJSONDIR="$HOME/projects/HearthstoneJSON/build/html/v1/$BUILD"

# Symlink file for extracted data
HSBUILDDIR="$BUILDDIR/extracted/$BUILD"

# Patch downloader
DOWNLOAD_BIN="$HOME/bin/ngdp-get"

# ILSpy decompiler script
DECOMPILER_BIN="$BASEDIR/decompiler/build/decompile.exe"
DECRYPT_BIN="$BASEDIR/decompiler/decrypt.py"

DECOMPILED_DIR="$BUILDDIR/decompiled/$BUILD"
DECOMPILED_OSX_DIR="$BUILDDIR/OSX-decompiled/$BUILD"

# Directory for decompiled protofiles
# Matches constant in commit.sh
PROTO_DIR="$BUILDDIR/protos/$BUILD"

# Script that delegates the placement of certain proto files
# This file should be copied from Proto-Extractor repo
PROTO_PACKAGE_FILE="$BASEDIR/proto-extractor/build/packaging.ini"
# This file should be build (with dependancies copied) from Proto-Extractor repo
PROTO_EXTRACTOR_BIN="$BASEDIR/proto-extractor/build/mono-extractor.exe"

# Autocommit script
COMMIT_BIN="$BASEDIR/commit.sh"

# CardDefs.xml processing
PROCESS_CARDXML_BIN="$BASEDIR/process_cardxml.py"

# Card texture extraction/generation script
TEXTUREGEN_BIN="$BASEDIR/generate_card_textures.py"

# Smartdiff generation script
SMARTDIFF_BIN="$BASEDIR/scripts/smartdiff_cardxml.py"

# Smartdiff output file
SMARTDIFF_OUT="$HOME/smartdiff-$BUILD.txt"

# Python requirements for the various scripts
REQUIREMENTS_TXT="$BASEDIR/requirements.txt"


function upgrade_venv() {
	if [[ -z $VIRTUAL_ENV ]]; then
		>&2 echo "Must be run from within a virtualenv"
		exit 1
	else
		pip install --upgrade pip setuptools
		pip install -r "$REQUIREMENTS_TXT" --upgrade --no-cache-dir
	fi
}


function update_repositories() {
	echo "Updating repositories"
	repos=("$SUNWELL_GIT" "$HSFONTS_GIT" "$HSDATA_GIT" "$HSCODE_GIT" "$HSPROTO_GIT")

	if [[ ! -d "$SUNWELL_GIT" ]]; then
		git clone git@github.com:HearthSim/Sunwell.git "$SUNWELL_GIT"
	fi

	if [[ ! -d "$HSFONTS_GIT" ]]; then
		git clone git@github.com:HearthSim/hs-fonts.git "$HSFONTS_GIT"
	fi

	if [[ ! -d "$HSDATA_GIT" ]]; then
		git clone git@github.com:HearthSim/hsdata.git "$HSDATA_GIT"
	fi

	if [[ ! -d "$HSCODE_GIT" ]]; then
		git clone git@github.com:HearthSim/hscode.git "$HSCODE_GIT"
	fi

	if [[ ! -d "$HSPROTO_GIT" ]]; then
		git clone git@github.com:HearthSim/hsproto.git "$HSPROTO_GIT"
	fi

	for repo in "${repos[@]}"; do
		git -C "$repo" pull
	done
}


function check_commit_sh() {
	if ! grep -q "$BUILD" "$COMMIT_BIN"; then
		>&2 echo "$BUILD is not present in $COMMIT_BIN. Aborting."
		exit 3
	fi
}


function prepare_patch_directories() {
	echo "Preparing patch directories"

	if [[ -e $HSBUILDDIR ]]; then
		echo "$HSBUILDDIR already exists, not overwriting."
	else
		mkdir -p "$(dirname "$HSBUILDDIR")"
		if [[ -d $HS_RAW_BUILDDIR ]]; then
			echo "$HS_RAW_BUILDDIR already exists... skipping download checks."
		else
			if ! [[ -d "$NGDP_OUT" ]]; then
				>&2 echo "No '$NGDP_OUT' directory. Run cd $NGDP_DIR && $DOWNLOAD_BIN"
				exit 2
			fi
			echo "Moving $NGDP_OUT to $HS_RAW_BUILDDIR"
			mv "$NGDP_OUT" "$HS_RAW_BUILDDIR"
		fi
		echo "Creating symlink to build in $HSBUILDDIR"
		ln -s -v "$HS_RAW_BUILDDIR" "$HSBUILDDIR"
	fi
}


function process_cardxml() {
	mkdir -p "$PROCESSED_DIR"

	echo "Extracting and processing CardDefs.xml file"

	# Panic? cardxml_raw_extract.py can extract the raw carddefs
	# Coupled with a manual process_cardxml.py --raw, can gen CardDefs.xml

	"$PROCESS_CARDXML_BIN" "$HSBUILDDIR" -o "$PROCESSED_DIR/CardDefs.xml"
	cp -rf "$HSBUILDDIR/Strings" -t "$PROCESSED_DIR"
}


function _decompile() {
	mkdir -p "$2"
	python3 "$DECRYPT_BIN" "$1/Assembly-CSharp.dll" "$1/Assembly-CSharp.decrypted.dll"
	mono "$DECOMPILER_BIN" "$1/Assembly-CSharp.decrypted.dll" "$2"
	rm -f "$1/Assembly-CSharp.decrypted.dll"
	mono "$DECOMPILER_BIN" "$1/Assembly-CSharp-firstpass.dll" "$2"
}


function decompile_code_win() {
	echo "Decompiling the Assemblies (Win)"

	dlldir="$HSBUILDDIR/Hearthstone_Data/Managed"
	_decompile "$dlldir" "$DECOMPILED_DIR"
}


function decompile_code_osx() {
	echo "Decompiling the Assemblies (OSX)"

	dlldir="$HSBUILDDIR/Hearthstone.app/Contents/Resources/Data/Managed"
	_decompile "$dlldir" "$DECOMPILED_OSX_DIR"
}

function extract_protos() {
	echo "Extracting PROTOS"
	mkdir -p "$PROTO_DIR"

	# First decrypt libraries for Windows context
	dlldir="$HSBUILDDIR/Hearthstone_Data/Managed"
	python3 "$DECRYPT_BIN" "$dlldir/Assembly-CSharp.dll" "$dlldir/Assembly-CSharp.decrypted.dll"

	dll_primary="$dlldir/Assembly-CSharp.decrypted.dll"
	dll_firstpass="$dlldir/Assembly-CSharp-firstpass.dll"

	# Run the Proto-Extractor on the libraries above
	mono "$PROTO_EXTRACTOR_BIN" --libPath "$dlldir" --outPath "$PROTO_DIR" \
		--proto3 --automatic-packaging --manual-package-file "$PROTO_PACKAGE_FILE" \
		"$dll_primary" "$dll_firstpass"

	# Remove the decrypted dll file
	rm -f "$dlldir/Assembly-CSharp.decrypted.dll"
}


function generate_git_repositories() {
	echo "Generating git repositories"

	if ! git -C "$HSDATA_GIT" rev-parse "$BUILD" &>/dev/null; then
		"$COMMIT_BIN" "hsdata" "$BUILD"
	else
		echo "Tag $BUILD already present in $HSDATA_GIT - Not committing."
	fi

	if ! git -C "$HSCODE_GIT" rev-parse "$BUILD" &>/dev/null; then
		"$COMMIT_BIN" "hscode" "$BUILD"
	else
		echo "Tag $BUILD already present in $HSCODE_GIT - Not committing."
	fi

	if ! git -C "$HSPROTO_GIT" rev-parse "$BUILD" &>/dev/null; then
		"$COMMIT_BIN" "hsproto" "$BUILD"
	else
		echo "Tag $BUILD already present in $HSPROTO_GIT - Not committing."
	fi

	echo "Pushing to GitHub"
	git -C "$HSDATA_GIT" push --follow-tags -f
	git -C "$HSCODE_GIT" push --follow-tags -f
	git -C "$HSCODE_GIT" push --follow-tags -f origin OSX:OSX
	git -C "$HSPROTO_GIT" push --follow-tags -f
}


function generate_smartdiff() {
	git -C "$HSDATA_GIT" show "$BUILD:CardDefs.xml" > /tmp/new.xml
	git -C "$HSDATA_GIT" show "$BUILD~:CardDefs.xml" > /tmp/old.xml

	echo "Generating smartdiff"
	"$SMARTDIFF_BIN" "/tmp/old.xml" "/tmp/new.xml" > "$SMARTDIFF_OUT"
	echo "Generated smartdiff in $SMARTDIFF_OUT"
	rm /tmp/new.xml /tmp/old.xml
}


function update_hearthstonejson() {
	echo "Updating HearthstoneJSON"
	if [[ -e $HSJSONDIR ]]; then
		echo "HearthstoneJSON is up-to-date."
	else
		"$HEARTHSTONEJSON_BIN" "$BUILD"
	fi
}


function extract_card_textures() {
	echo "Extracting card textures"
	"$TEXTUREGEN_BIN" "$HSBUILDDIR/Data/Win/"{rad_base,card,premiummaterials,shared}*.unity3d --outdir="$CARDARTDIR" --skip-existing
	"$HEARTHSTONEJSON_BIN" sync-textures "$CARDARTDIR"
}


function main() {
	upgrade_venv
	update_repositories
	check_commit_sh
	prepare_patch_directories
	process_cardxml
	decompile_code_win
	decompile_code_osx
	extract_protos
	generate_git_repositories
	generate_smartdiff
	extract_card_textures
	update_hearthstonejson

	echo "Build $BUILD completed"
}


main "$@"
