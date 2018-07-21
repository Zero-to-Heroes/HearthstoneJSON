#!/usr/bin/env python

import json
import requests
from getpass import getpass
from bs4 import BeautifulSoup


LOGIN_URL = "https://eu.battle.net/login/en-us/?app=wtcg"


def main():
	session = requests.session()
	r = session.get(LOGIN_URL)
	soup = BeautifulSoup(r.text, "html.parser")
	csrftoken = soup.find("input", {"id": "csrftoken"})

	formdata = {
		"csrftoken": csrftoken.attrs["value"],
		"accountName": input("Battle.net email: ").strip(),
		"password": getpass("Password: ").strip(),
	}

	post = session.post(LOGIN_URL, formdata, allow_redirects=False)
	# You generally want gs-hs cookie, or the location
	data = dict(post.cookies)
	data["LOCATION"] = post.headers.get("Location", "")
	print(json.dumps(data))


if __name__ == "__main__":
	main()
