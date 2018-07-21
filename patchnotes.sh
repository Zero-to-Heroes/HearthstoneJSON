#!/bin/bash

# Get current Battle.net patchnotes
# Requires lynx.


function patchnotes {
	ua="Battle.net/1.0.8.4217"
	_baseurl="https://us.battle.net/connect/"
	usage="usage: $0 <product> [live|ptr|beta] [language]\nproduct is one of wow, s2, d3, heroes, wtcg"

	hash lynx 2>/dev/null || {
		>&2 echo "You need to install Lynx first."
		return 1
	}

	if [[ $1 == ("--help"|"-h") ]]; then
		>&2 echo "$usage"
		return 0
	fi

	prog="$1"
	if [[ $# == 1 ]]; then
		product="live"
		lang="en"
	elif [[ $# == 2 ]]; then
		product="$2"
		lang="en"
	elif [[ $# == 3 ]]; then
		product="$2"
		lang="$3"
	else
		>&2 echo "$usage"
		return 1
	fi

	lynx -dump -display_charset="UTF-8" -useragent="$ua" "$_baseurl/$lang/app/$prog/patch-notes?productType=$product" 2> /dev/null
}
