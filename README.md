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

Files will be generated in the `out` directory.

The `generate_audio` outputs a `sound_effects.json` file that maps the card IDs to the name of the sound files that are played for specific events (typically play / attack / death for minions).
The files themselves can be obtained by running the unityextract script from the unitypack project


## License

This project is licensed under the terms of the MIT license.
The full license text is available in the `LICENSE` file.


## Community

This is a [HearthSim](https://hearthsim.info) project. All development
happens on our IRC channel `#hearthsim` on [Freenode](https://freenode.net).
