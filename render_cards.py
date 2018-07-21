#!/usr/bin/env python

import json

import boto3
from hearthstone import cardxml
from hearthstone.enums import CardType, Locale


FUNCTION_NAME = "sunwell-lambda-dev-render"


def main():
	LAMBDA = boto3.client("lambda")
	db, _ = cardxml.load_dbf()
	for card in db.values():
		if card.type == CardType.ENCHANTMENT:
			continue
		print("Rendering %r" % (card.card_id))

		for locale in Locale:
			if locale.unused:
				continue

			for resolution in (256, 512):
				LAMBDA.invoke(
					FunctionName=FUNCTION_NAME,
					InvocationType="Event",
					Payload=json.dumps({
						"queryStringParameters": {
							"locale": locale.name,
							"template": card.card_id,
							"resolution": str(resolution),
						},
					})
				)


if __name__ == "__main__":
	main()
