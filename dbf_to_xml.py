#!/usr/bin/env python

import os
import sys
from argparse import ArgumentParser
from hearthstone.dbf import Dbf


class DbfConverter:
	def __init__(self):
		self._p = ArgumentParser()
		self._p.add_argument("files", nargs="+", type=str)
		self._p.add_argument("-o", "--outdir", nargs="?", type=str)

		self.dbfs = []

	def info(self, msg):
		sys.stderr.write("[INFO] %s\n" % (msg))

	def parse_bundle(self, path):
		import unitypack

		with open(path, "rb") as f:
			bundle = unitypack.load(f)
			asset = bundle.assets[0]
			self.info("Processing %r" % (asset))
			self.parse_dbf_asset(asset)

	def parse_dbf_asset(self, asset):
		for obj in asset.objects.values():
			if obj.class_id == 114 and obj.type.endswith("DbfAsset"):
				self.dbfs.append(self.dbf_from_unity_object(obj))

	def dbf_from_unity_object(self, obj):
		dbf = Dbf()
		dbf.populate_from_unity_object(obj)
		return dbf

	def run(self, args):
		self.args = self._p.parse_args(args)

		for f in self.args.files:
			self.parse_bundle(f)

		if not os.path.exists(self.args.outdir):
			os.makedirs(self.args.outdir)
		for dbf in self.dbfs:
			filename = os.path.join(self.args.outdir, dbf.name + ".xml")
			with open(filename, "wb") as f:
				f.write(dbf.to_xml())


def main():
	app = DbfConverter()
	app.run(sys.argv[1:])


if __name__ == "__main__":
	main()
