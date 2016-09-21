# process_podcast

This script enables you to assemble an ingterated podcast of a lecture or class from several different inputs, including:

* recorded audio
* screen recordings
* other video
* JPEG images representing individual lecture slides
* a PDF containing the lecture slides

Audio and video may come from the same file, or from separate files. You also have the ability to insert small “joiner” sections of audio and video between major “segments” of the podcast. You can even configure the “joiner” so that it repeats the last frame of the previous segment for the desired duration.

For help on command line options: `process_podcast.py --help`.

For help on the podcast configuration file format, see the [configuration file documentation][].


## Requirements

* Python 2.7 series. (Not tested with Python 3.)
* The `pyparsing` module. Linux: `pip install pyparsing`, `easy_install pyparsing`,  or whatever other method you normally use to install Python modules; macOS (MacPorts): `port install py-parsing`. Also see the [pyparsing documentation][].
* The `pexpect module`.  Linux: `pip install pexpect`, `easy_install pexpect`,  or whatever other method you normally use to install Python modules; macOS (MacPorts): `port install py-pexpect`. Also see the [pexpect documentation][].

[pyparsing documentation]: http://pyparsing.wikispaces.com/ "pyparsing documentation"
[pexpect documentation]: https://pexpect.readthedocs.io/en/stable/ "pexpect documentation"
[configuration file documentation]: config_help.md "configuration file documentation"
