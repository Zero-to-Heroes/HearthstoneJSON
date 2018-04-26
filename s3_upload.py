#!/usr/bin/env python

import sys
import boto3
from argparse import ArgumentParser
from pprint import pprint


API_BUCKET = "api.hearthstonejson.com"
ART_BUCKET = "art.hearthstonejson.com"


def update_website_configuration(s3, build, bucket=API_BUCKET):
	print("Querying website configuration for %r" % (bucket))
	orig_config = s3.get_bucket_website(Bucket=bucket)
	pprint(orig_config)

	if "ResponseMetadata" in orig_config:
		del orig_config["ResponseMetadata"]

	config = orig_config.copy()

	config["RoutingRules"] = [{
		"Condition": {
			"KeyPrefixEquals": "v1/latest/"
		},
		"Redirect": {
			"ReplaceKeyPrefixWith": "v1/%i/" % (build),
			"HttpRedirectCode": "302",
			"Protocol": "https",
		},
	}]

	if config != orig_config:
		print("Updating website configuration")
		pprint(config)
		s3.put_bucket_website(Bucket=bucket, WebsiteConfiguration=config)
	else:
		print("Website configuration up-to-date")


def main():
	parser = ArgumentParser()
	parser.add_argument("--build", type=int, nargs=1)
	parser.add_argument("dir", type=str, nargs="+")

	args = parser.parse_args(sys.argv[1:])
	s3 = boto3.client("s3")

	update_website_configuration(s3, args.build[0])


if __name__ == "__main__":
	main()
