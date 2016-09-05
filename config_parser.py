#!/usr/bin/env python

import sys

from pyparsing import *
# pyparsing documentation:
# https://sourceforge.net/p/pyparsing/code/HEAD/tree/trunk/src/HowToUsePyparsing.txt#l302


INPUTSPEC_DEFAULTS = {"type": None, "filename": None, "num": None}
TIMESTAMP_DEFAULTS = {"hh": 0, "mm": 0, "ms": 0}


# see http://stackoverflow.com/questions/11180622/optional-string-segment-in-pyparsing
def default_input_fields(fields):
    """Set missing input specification values to defaults."""
    set_defaults(fields, INPUTSPEC_DEFAULTS)


def default_timestamp_fields(fields):
    """Set missing timestamp values to defaults."""
    set_defaults(fields, TIMESTAMP_DEFAULTS)


def set_defaults(fields, defaults):
    """Set missing field values to defaults."""
    undefined = set(defaults.keys()) - set(fields.keys())
    for k in undefined:
        v = defaults[k]
        # see http://pyparsing.wikispaces.com/share/view/71042464
        fields[k] = v
        fields.append(v)


def parser_bnf():
    """Grammar for parsing podcast configuration files."""
    at = Literal("@").suppress()
    caret = Literal("^")
    colon = Literal(":").suppress()
    left_bracket = Literal("[").suppress()
    period = Literal(".").suppress()
    right_bracket = Literal("]").suppress()

    # zero_index ::= [0-9]+
    zero_index = Word(nums).setParseAction(lambda s, l, t: int(t[0]))

    # filename ::= [A-Za-z0-9][-A-Za-z0-9._ ]+
    filename_first = Word(alphanums, exact=1)
    filename_rest = Word(alphanums + "-_/. ")
    filename = Combine(filename_first + Optional(filename_rest))

    # millisecs ::= "." [0-9]+
    millisecs = (Word(nums).setParseAction(
                        lambda s, l, t: int(t[0][:3].ljust(3, "0")))
                    .setResultsName("ms"))

    # hours, minutes, seconds ::= zero_index
    hours = zero_index.setResultsName("hh")
    minutes = zero_index.setResultsName("mm")
    seconds = zero_index.setResultsName("ss")

    hours_minutes = hours + colon + minutes + colon | minutes + colon
    secs_millisecs = (seconds + Optional(period + millisecs) |
                      period + millisecs)

    # timestamp ::= [[hours ":"] minutes ":"] seconds ["." millisecs]
    timestamp = Optional(hours_minutes) + secs_millisecs

    # duration_file ::= "@", filename
    # We need a separate item for a lonely duration file timestamp so
    # that we can attach a parse action just to the lonely case. Using
    # duration_file alone means the parse action is attached to all
    # instances of duration_file.
    duration_file = at + filename.setResultsName("filename")
    lonely_duration_file = at + filename.setResultsName("filename")

    # timespecs ::= timestamp [duration_file | {timestamp}]
    # If duration_file timestamp is lonely, prepend a zero timestamp.
    timespecs = Or(
        [lonely_duration_file.setParseAction(
            lambda s, l, t: [timestamp.parseString("00:00:00.000"), t]),
         Group(timestamp) + duration_file,
         OneOrMore(Group(timestamp.setParseAction(default_timestamp_fields)))])
    
    # last_frame ::=  "-1" | "last"
    last_frame = oneOf(["-1", "last"]).setParseAction(replaceWith(-1))

    # frame_number ::= ":" (zero_index | last_frame)
    frame_number = colon - (zero_index | last_frame).setResultsName("num")

    # stream_number ::= ":" zero_index
    stream_number = colon - zero_index.setResultsName("num")

    # input_file ::= ":" [filename]
    input_file = colon - Optional(filename).setResultsName("filename")

    # previous_segment ::= ":" "^"
    previous_segment = colon - caret.setResultsName("filename")

    # frame_input_file ::= input_file | previous_segment
    frame_input_file = Or([input_file, previous_segment])

    # av_trailer ::= input_file [stream_number]
    av_trailer = input_file + Optional(stream_number)

    # frame_type ::= "frame" | "f"
    frame_type = oneOf(["f", "frame"]).setParseAction(replaceWith("frame"))

    # frame_input ::= frame_type [frame_input_file [frame_number]]
    frame_input = (frame_type.setResultsName("type") +
                   Optional(frame_input_file + Optional(frame_number)))

    # video_type ::= "video" | "v"
    video_type = oneOf(["v", "video"]).setParseAction(replaceWith("video"))

    # audio_type ::= "audio" | "a"
    audio_type = oneOf(["a", "audio"]).setParseAction(replaceWith("audio"))

    # av_input ::= (audio_type | video_type) [av_trailer]
    av_input = ((audio_type | video_type).setResultsName("type") +
                Optional(av_trailer))

    # inputspec ::= "[" (av_input | frame_input) "]"
    inputspec = (left_bracket + 
                 delimitedList(av_input | frame_input, delim=":")
                        .setParseAction(default_input_fields) -
                 right_bracket)

    # segmentspec ::= inputspec [timespecs]
    segmentspec = Group(inputspec + 
                        Group(Optional(timespecs)).setResultsName("times"))

    # config ::= {segmentspec}
    config = ZeroOrMore(segmentspec)
    config.ignore(pythonStyleComment)
    
    return config


def parse_configuration_file(config_file):
    """Parse a podcast configuration file."""
    try:
        parser = parser_bnf()
        result = parser.parseFile(config_file, parseAll=True)
    except (ParseException, ParseSyntaxException) as e:
        print("ERROR: {m}".format(m=str(e)))
        sys.exit(1)
    return result


def parse_configuration_string(config_string):
    """Parse a podcast configuration file."""
    try:
        parser = parser_bnf()
        result = parser.parseString(config_string, parseAll=True)
    except (ParseException, ParseSyntaxException) as e:
        print("ERROR: {m}".format(m=str(e)))
        sys.exit(1)
    return result


def test_parser():
    tests = ["test/config1.txt", "test/config2.txt", "test/config3.txt", "test/config4.txt", "test/config5.txt"]

    for t in tests:
        print "==={f}===".format(f=t)
        r = parse_configuration_file(t)
        for s in r:
            print s
            print "    type = {t}".format(t=s["type"])
            print "    filename = '{f}'".format(f=s["filename"])
            print "    num = {n}".format(n=s["num"])
            print "    times = {t}".format(t=s["times"])
            for i, t in enumerate(s["times"]):
                if (isinstance(t, str)):
                    print "        punch out after duration of '{f}'".format(f=t)
                if (isinstance(t, ParseResults)):
                    if (i % 2 == 0):
                        print "        punch in at:  {hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}".format(hh=t["hh"], mm=t["mm"], ss=t["ss"], ms=t["ms"])
                    else:
                        print "        punch out at: {hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}".format(hh=t["hh"], mm=t["mm"], ss=t["ss"], ms=t["ms"])
        print


if (__name__ == "__main__"):
    test_parser()
