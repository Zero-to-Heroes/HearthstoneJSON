# Hearthstone JSON

This project extracts card data from Hearthstone into JSON files to be
used to generate [HearthstoneJSON.com](https://hearthstonejson.com)


## Requirements

* Python >= 3.4
* [python-hearthstone](https://github.com/HearthSim/python-hearthstone.git)


## Generate

To generate the files, just run:

* `./bootstrap.sh`
* `./generate.py`
* `./generate_audio.py /d/Games/Hearthstone/Data/**/*.unity3d`

The `generate_audio` currently fails to find the sound files associated to the cards in Scholomance (and the previous expansion).
More specifically, in the `extract_sound_file_names` method, the `guid_to_path` doesn't contain the `guid` from these cards.

Files will be generated in the `out` directory.


## License

This project is licensed under the terms of the MIT license.
The full license text is available in the `LICENSE` file.


## Community

This is a [HearthSim](https://hearthsim.info) project. All development
happens on our IRC channel `#hearthsim` on [Freenode](https://freenode.net).
