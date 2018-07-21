#!/bin/bash
set -e

BASEDIR="$(readlink -f "$(dirname "$0")")"
BUILDDIR="$BASEDIR/build"
HTMLDIR="$BUILDDIR/html"
OUTDIR="$HTMLDIR/v1"
PYTHON=${PYTHON:-python}
GENERATE_STRINGS_BIN="$BASEDIR/generate_strings.py"
GENERATE_BIN="$BASEDIR/generate_hearthstonejson.py"
S3_UPLOAD_BIN="$BASEDIR/s3_upload.py"
ENUMS_JSON="$OUTDIR/enums.json"
ENUMS_CS="$OUTDIR/enums.cs"
ENUMS_TS="$OUTDIR/enums.d.ts"

HSDATA_URL="https://github.com/HearthSim/hs-data.git"
HSDATA_DIR="$BASEDIR/hsdata.git"

# AWS configuration
S3_BUCKET_NAME="api.hearthstonejson.com"
S3_ART_BUCKET_NAME="art.hearthstonejson.com"


function update_repos() {
	pip install --upgrade hearthstone

	if [[ -d $HSDATA_DIR ]]; then
		git -C "$HSDATA_DIR" fetch --tags
		git -C "$HSDATA_DIR" fetch --tags "$HSDATA_URL"
		git -C "$HSDATA_DIR" reset --hard FETCH_HEAD
	else
		git clone "$HSDATA_URL" "$HSDATA_DIR"
	fi
}

function update_enums() {
	"$PYTHON" -m hearthstone.enums > "$ENUMS_JSON"
	"$PYTHON" -m hearthstone.enums --cs > "$ENUMS_CS"
	"$PYTHON" -m hearthstone.enums --ts > "$ENUMS_TS"
}

function update_strings() {
	"$PYTHON" "$GENERATE_STRINGS_BIN" -o "$OUTDIR/strings"
}

function update_build() {
	build="$1"
	git -C "$HSDATA_DIR" reset --hard "$build"
	mkdir -p "$OUTDIR"
	"$PYTHON" "$GENERATE_BIN" --input-dir="$HSDATA_DIR" --output-dir="$OUTDIR/$build"
}

function update_indexes() {
	_tree="tree -I index.html -L 2 -T HearthstoneJSON"
	for build in "$OUTDIR"/*/; do
		build="$(basename $build)"
		$_tree -H "/v1/$build" "$OUTDIR/$build" > "$OUTDIR/$build/index.html"
		for subdir in "$OUTDIR/$build"/*/; do
			$_tree -H "/v1/$build/$(basename $subdir)" "$subdir" > "$subdir/index.html"
		done
	done

	$_tree -H "" "$HTMLDIR" > "$HTMLDIR/index.html"
	$_tree -H "/v1" "$OUTDIR" > "$OUTDIR/index.html"
}

function upload_to_s3() {
	build="$1"

	aws s3 sync "$OUTDIR" "s3://$S3_BUCKET_NAME/v1"
	"$PYTHON" "$S3_UPLOAD_BIN" --build="$build" "$OUTDIR"
}


mkdir -p "$BUILDDIR"

update_repos
builds=($(printf "%s\n" $(git -C "$HSDATA_DIR" tag) | sort -n))
maxbuild="${builds[-1]}"

if [[ -z $1 || $1 == "latest" ]]; then
	echo "Updating latest build"
	update_build "$maxbuild"
	update_enums
	update_strings
	update_indexes
	upload_to_s3 "$maxbuild"
elif [[ $1 == "clean-upload" ]]; then
	echo "Preparing for S3 upload"
	update_enums
	update_strings
	update_indexes
	aws s3 rm "s3://$S3_BUCKET_NAME" --recursive
	upload_to_s3 "$maxbuild"
elif [[ $1 == "sync-textures" ]]; then
	echo "Syncing textures to S3"
	if [[ -z $2 ]]; then
		>&2 echo "Usage: $0 $1 <input dir>"
		exit 2
	fi
	aws s3 sync "$2" "s3://$S3_ART_BUCKET_NAME/v1"
elif [[ $1 == "all" ]]; then
	echo "Updating all builds"
	for build in ${builds[@]}; do
		echo $build
		update_build "$build"
	done
	update_strings
	update_indexes
	exit 1
elif [[ $1 =~ ^[0-9]+$ ]]; then
	echo "Updating build $1"
	update_build "$1"
	update_indexes "$1"
	if [[ $1 == $maxbuild ]]; then
		update_strings
		update_enums
	fi
	upload_to_s3 "$maxbuild"
else
	>&2 echo "Usage: $0 [BUILD | latest | all | clean-upload]"
fi
