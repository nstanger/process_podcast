#!/usr/bin/env python

from pyparsing import *

# pyparsing documentation:
# https://sourceforge.net/p/pyparsing/code/HEAD/tree/trunk/src/HowToUsePyparsing.txt#l302


STREAM_FIELDS = {"type", "filename", "num"}


# see http://stackoverflow.com/questions/11180622/optional-string-segment-in-pyparsing
def assign_missing_fields(fields):
    """Fill in missing optional field values (filename, num)."""
    not_found = STREAM_FIELDS - set(fields.keys())
    for k in not_found:
        v = None
        # see http://pyparsing.wikispaces.com/share/view/71042464
        fields[k] = v
        fields.append(v)


def parser_bnf():
    """Grammar for parsing podcast configuration files."""

    at = Literal("@").suppress()
    caret = Literal("^")
    colon = Literal(":").suppress()
    comment_char = Literal("#")
    hyphen = Literal("-")
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
    millisecs = (period + 
                 (Word(nums).setParseAction(
                        lambda s, l, t: int(t[0][:3].ljust(3, "0")))
                    .setResultsName("ms")))

    # hours, minutes, seconds ::= zero_index
    hours = zero_index.setResultsName("hh")
    minutes = zero_index.setResultsName("mm")
    seconds = zero_index.setResultsName("ss")

    # timestamp ::= hours ":" minutes ":" seconds [millisecs]
    timestamp = Group(hours + colon + minutes + colon + seconds + 
                      Optional(millisecs))

    # duration_file ::= "@", filename
    # We need a separate item for a lonely duration file timestamp so
    # that we can attach a parse action just to the lonely case. Using
    # duration_file alone means the parse action is attached to all
    # instances of duration_file.
    duration_file = at + filename
    lonely_duration_file = at + filename

    # timespecs ::= timestamp [duration_file | {timestamp}]
    # If duration_file timestamp is lonely, prepend a zero timestamp.
    timespecs = Or(
        [lonely_duration_file.setParseAction(
            lambda s, l, t: timestamp.parseString("00:00:00.000") + t),
         timestamp + duration_file,
         OneOrMore(timestamp)])

    # last_frame ::=  "-1" | "last"
    last_frame = oneOf(["-1", "last"]).setParseAction(replaceWith(-1))

    # frame_number ::= ":" (zero_index | last_frame)
    frame_number = colon + Or([zero_index, last_frame]).setResultsName("num")

    # stream_number ::= ":" zero_index
    stream_number = colon + zero_index.setResultsName("num")

    # input_file ::= ":" [filename]
    input_file = colon + Optional(filename).setResultsName("filename")

    # previous_segment ::= ":" "^"
    previous_segment = colon + caret.setResultsName("filename")

    # frame_input_file ::= input_file | previous_segment
    frame_input_file = Or([input_file, previous_segment])

    # frame_type ::= "frame" | "f"
    frame_type = oneOf(["f", "frame"]).setParseAction(replaceWith("frame"))

    # frame_input ::= frame_type [frame_input_file [frame_number]]
    frame_input = (frame_type.setResultsName("type") +
                   Optional(frame_input_file +
                   Optional(frame_number)))

    # video_type ::= "video" | "v"
    video_type = oneOf(["v", "video"]).setParseAction(replaceWith("video"))

    # video_input ::= video_type [input_file [stream_number]]
    video_input = (video_type.setResultsName("type") +
                   Optional(input_file +
                   Optional(stream_number)))

    # audio_type ::= "audio" | "a"
    audio_type = oneOf(["a", "audio"]).setParseAction(replaceWith("audio"))

    # audio_input ::= audio_type [input_file [stream_number]]
    audio_input = (audio_type.setResultsName("type") +
                   Optional(input_file + Optional(stream_number)))

    # audio_or_video_input ::= audio_input | video_input
    audio_or_video_input = Or([audio_input, video_input])

    # inputspec ::= "[" (audio_or_video_input | frame_input) "]"
    inputspec = (left_bracket +
                 delimitedList(
                    Or([audio_or_video_input, frame_input]), delim=":")
                        .setParseAction(assign_missing_fields) +
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
    parser = parser_bnf()
    return parser.parseFile(config_file, parseAll=True)


def parse_configuration_string(config_string):
    """Parse a podcast configuration file."""
    parser = parser_bnf()
    return parser.parseString(config_string, parseAll=True)


def test_parser():
    tests = ["test/config1.txt", "test/config2.txt", "test/config3.txt", "test/config4.txt"]

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
