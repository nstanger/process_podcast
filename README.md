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

* FFmpeg.
* ImageMagick.
* Python 3.5 or later with the following modules:
  * `pyparsing`; Linux: `pip install pyparsing`, `easy_install pyparsing`,  or whatever other method you normally use to install Python modules; macOS (MacPorts): `port install py-parsing`. Also see the [pyparsing documentation][].
  * `pexpect`; Linux: `pip install pexpect`, `easy_install pexpect`,  or whatever other method you normally use to install Python modules; macOS (MacPorts): `port install py-pexpect`. Also see the [pexpect documentation][].
  * There is a `requirements.txt` that you can use to quickly install all the required modules.

[pyparsing documentation]: http://pyparsing.wikispaces.com/ "pyparsing documentation"
[pexpect documentation]: https://pexpect.readthedocs.io/en/stable/ "pexpect documentation"
[configuration file documentation]: config_help.md "configuration file documentation"

## Testing

Run `python -m unittest` at the root level of the project to run all unit tests.
