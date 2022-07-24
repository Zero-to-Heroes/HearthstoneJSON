# Hearthstone JSON

This project extracts card data from Hearthstone into JSON files to be
used to generate [HearthstoneJSON.com](https://hearthstonejson.com)

## Requirements

- Python >= 3.4

## Generate

To generate the files, just run:

- `pip install -r requirements.txt`
- `./generate_audio.py /e/Games/Hearthstone/Data/Win`
- `./generate_card_backs.py /e/Games/Hearthstone/Data/Win`

Files will be generated in the `out` directory.

The `generate_audio` outputs a `sound_effects.json` file that maps the card IDs to the name of the sound files that are played for specific events (typically play / attack / death for minions).
The files themselves can be obtained by running the unityextract script from the unitypack project

## License

This project is licensed under the terms of the MIT license.
The full license text is available in the `LICENSE` file.

## Community

This is a tool used by [Firestone](https://www.firestoneapp.com/).  
You can come say hi on [our Discord](https://discord.gg/FhEHn8w)
