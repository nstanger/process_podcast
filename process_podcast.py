#!/usr/bin/env python

import argparse
import datetime
import logging
import os.path
import sys

from pyparsing import ParseResults

import globals
from config_parser import (
    parse_configuration_file, parse_configuration_string)
from shell_command import (FFprobeCommand, FFmpegConcatCommand)
from segment import (Segment, AudioSegment, VideoSegment, FrameSegment)


class InputStreamAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        input = values.split(":")
        file = input[0]
        stream = None if (len(input) == 1) else input[1]
        setattr(namespace, self.dest, file)
        if (option_string in ["--audio", "-a"]):
            setattr(namespace, 'audio_stream_number', stream)
        elif (option_string in ["--video", "-v"]):
            setattr(namespace, 'video_stream_number', stream)


def parse_command_line():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        usage="%(prog)s [options] <output>",
        description="where: <output> is the name of the output file "
            "(note: .mov is generally best)",
        epilog="Default input streams can be specified using either of "
            "--audio or --video. If neither of these are specified, "
            "then you must supply a configuration file using --config. "
            "(Of course, you can always supply a configuration file "
            "regardless.)\n\n"
            "Input streams can be taken from the same input file.\n\n"
            "If no segments are specified, the entire input stream is "
            "processed as one segment. The number and duration of segments "
            "can differ, but all input streams must have the same the total "
            "length.")
    
    parser.add_argument(
        "output",
        help="name of the output file (note: .mov is best)")
    
    parser.add_argument(
        "--audio", "-a", metavar="FILE[:STREAM]", action=InputStreamAction,
        help="File name for the default audio input stream (can be the "
            "same as other input streams). You can optionally specify "
            "the default audio stream number to use if the file contains "
            "more than one (this can be overidden in a configuration "
            "file). If you don't specify a stream number, it defaults "
            "to 0 (i.e., the first audio stream in the file).")
    
    parser.add_argument(
        "--configuration", "--config", "-c", dest="config", metavar="FILE",
        help="File name for the podcast segment configuration (plain text). "
            "Run {p} --help-config for details on the file "
            "format.".format(p=globals.PROGRAM))
    
    parser.add_argument(
        "--debug", "-d", action="store_true",
        help="Print debugging output (overrides --quiet).")
    
    parser.add_argument(
        "--keep", "-k", action="store_true",
        help="Don't delete any generated temporary files.")
    
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Mute all console output (overridden by --debug).")

    parser.add_argument(
        "--video", "-v", metavar="FILE[:STREAM]", action=InputStreamAction,
        help="File name for the default video input stream (can be the "
            "same as other input streams). You can optionally specify "
            "the default video stream number to use if the file contains "
            "more than one (this can be overidden in a configuration "
            "file). If you don't specify a stream number, it defaults "
            "to 0 (i.e., the first video stream in the file).")
    
    args = parser.parse_args()
    
    return args


def print_config_help():
    """Print details of the configuration file format."""
    print "Help is coming."
    sys.exit(0)


def check_arguments(args):
    """Sanity check the command line arguments."""
    fn = "check_arguments"
#     if (args.help_config):
#         print_config_help()
    
    if (args.quiet):
        globals.log.setLevel(logging.WARNING)
        
    # --debug overrides --quiet.
    if (args.debug):
        globals.log.setLevel(logging.DEBUG)
        globals.log.debug("{fn}(): args = {a}".format(fn=fn, a=args))
    
    # Must specify at least one of --audio, --video, --config.
    if (not any([args.audio, args.video, args.config])):
        globals.log.error("must specify at least one of --audio, --video, "
                          "or --config")
        sys.exit(1)
    

def get_configuration(args):
    # Fill in missing file names for default input streams.
    fn = "get_configuration"
    type_mapping = {
        "audio": {"file": args.audio, "stream": args.audio_stream_number},
        "video": {"file": args.video, "stream": args.video_stream_number}}
    globals.log.info("Processing configuration...")
    if (args.config):
        config = parse_configuration_file(args.config)
        # Check that applicable default input streams have been specified.
        for i, c in enumerate(config):
            type = c["type"]
            if (type in type_mapping):
                file = type_mapping[type]["file"]
                stream = type_mapping[type]["stream"]
                # No filename in configuration.
                if (not c["filename"]):
                    if (file):
                        config[i]["filename"] = file
                    # No filename on command line either.
                    else:
                        globals.log.error(
                            "attempting to use default {s} input stream, but "
                            "--{s} hasn't been specified".format(s=type))
                        sys.exit(1)
                # No stream number in configuration. Note: 0 is a valid
                # stream number, so explicitly check for None.
                if (c["num"] is None):
                    # Assume 0 if no stream on command line either.
                    config[i]["num"] = 0 if stream is None else stream
    else:
        conf_list = []
        for m in type_mapping:
            file = type_mapping[m]["file"]
            stream = type_mapping[m]["stream"]
            if (file and stream is not None):
                conf_list += [
                    "[{type}:{file}:{stream}]".format(type=m, file=file,
                                                      stream=stream)]
        globals.log.debug("{fn}(): default config = "
                          "{c}".format(fn=fn, c=conf_list))
        config = parse_configuration_string("\n".join(conf_list))
    
    return config


def get_file_duration(file):
    """Calculate the duration a media file as a timedelta object."""
    command = FFprobeCommand(
        ["-show_entries", "format=duration",
         "-print_format", "default=noprint_wrappers=1:nokey=1",
        file])
    ss, ms = command.get_output().strip().split(".")
    ms = ms[:3].ljust(3, "0")
    return datetime.timedelta(seconds=int(ss), milliseconds=int(ms))


def make_new_segment(type, filename, punch_in, punch_out, num):
    """Make a new segment instance of the correct class."""
    fn = "make_new_segment"
    globals.log.debug("{fn}(): type = {t}".format(fn=fn, t=type))
    globals.log.debug("{fn}(): filename = {f}".format(fn=fn, f=filename))
    globals.log.debug("{fn}(): punch in = {i}s".format(fn=fn, i=punch_in))
    globals.log.debug("{fn}(): punch out = {o}s".format(fn=fn, o=punch_out))
    globals.log.debug("{fn}(): num = {n}".format(fn=fn, n=num))
    
    if (type == "audio"):
        return AudioSegment(file=filename, punch_in=punch_in,
                            punch_out=punch_out, input_stream=num)
    elif (type == "video"):
        return VideoSegment(file=filename, punch_in=punch_in,
                            punch_out=punch_out, input_stream=num)
    elif (type == "frame"):
        return FrameSegment(file=filename, punch_in=punch_in,
                            punch_out=punch_out, input_stream=num)
    else:
        return None


def process_timestamp_pair(times):
    """Constructs timedelta instances from a pair of config timestamps."""
    fn = "process_timestamp_pair"
    globals.log.debug("{fn}(): t0 = {t}".format(fn=fn, t=times[0]))
    globals.log.debug("{fn}(): t1 = {t}".format(fn=fn, t=times[1]))
    
    # If the first item in the timestamp list in the configuration file
    # is a filename, the parser inserts a zero timestamp before it. We
    # can therefore guarantee that the first item of the pair will
    # always be a timestamp.
    t0 = datetime.timedelta(
        hours=times[0]["hh"], minutes=times[0]["mm"],
        seconds=times[0]["ss"], milliseconds=times[0]["ms"])
    if (isinstance(times[1], str)):
        t1 = t0 + get_file_duration(times[1])
    elif (isinstance(times[1], ParseResults)):
        t1 = datetime.timedelta(
            hours=times[1]["hh"], minutes=times[1]["mm"],
            seconds=times[1]["ss"], milliseconds=times[1]["ms"])
    else:
        globals.log.error("unreadable timestamp {t}".format(t=times[1]))
    
    return t0, t1


def process_time_list(type, filename, num, time_list):
    """Process an audio or video stream and build a list of segments."""
    if (os.path.exists(filename)):
        stream_duration = get_file_duration(filename)
    else:
        stream_duration = 0
    segments = []
    
    # No timestamps: punch in at 0, out at stream duration.
    if (len(time_list) == 0):
        punch_in = datetime.timedelta()
        punch_out = stream_duration
        segments.append(make_new_segment(type, filename, punch_in,
                                         punch_out, num))
    else:
        # Process each pair of timestamps as punch in, out. If there's
        # an odd number of items, the last one is processed separately.
        for t in zip(time_list[::2], time_list[1::2]):
            punch_in, punch_out = process_timestamp_pair(t)
            if (punch_in == punch_out):
                globals.log.warning(
                    "punch in ({i}s) and punch out ({o}s) times are "
                    "equal; no segment will be "
                    "generated".format(i=punch_in.total_seconds(),
                                       o=punch_out.total_seconds()))
                continue
            elif (punch_out < punch_in):
                globals.log.error(
                    "punch out time ({i}s) falls before punch in time "
                    "({o}s); can't generate a valid "
                    "segment".format(i=punch_in.total_seconds(),
                                     o=punch_out.total_seconds()))
                sys.exit(1)
            segments.append(make_new_segment(type, filename, punch_in,
                                             punch_out, num))
    
    # Odd number of timestamps: punch in at last timestamp,
    # out at stream duration.
    if (len(time_list) % 2 != 0):
        punch_in, _ = process_timestamp_pair([time_list[-1], None])
        punch_out = stream_duration - punch_in
        segments.append(make_new_segment(type, filename, punch_in,
                                         punch_out, num))
    return segments


def process_input_streams(config):
    """Process a list of stream specification and build a list of segments."""
    fn = "process_input_streams"
    globals.log.info("Processing input streams...")
    segments = []
    for cnf in config:
        globals.log.debug("{fn}(): type = {t}".format(fn=fn, t=cnf["type"]))
        globals.log.debug(
            "{fn}(): filename = {f}".format(fn=fn, f=cnf["filename"]))
        globals.log.debug("{fn}(): num = {n}".format(fn=fn, n=cnf["num"]))
        globals.log.debug("{fn}(): times = t".format(fn=fn, t=cnf["times"]))
    
        segments += process_time_list(cnf["type"], cnf["filename"],
                                      cnf["num"], cnf["times"])  
    return segments



def render_podcast(segments, output):
    """Stitch together the various input components into the final podcast."""
    fn = "render_podcast"
    globals.log.info("Rendering final podcast...")
    command = FFmpegConcatCommand()
    input_files = Segment.input_files()
    for f in input_files:
        if (input_files[f]):
            command.append_input_options(input_files[f])
        command.append_input_options(["-i", f])
    for s in segments:
        if (not isinstance(s, FrameSegment)):
            command.append_filter(s.trim_filter())
    command.append_concat_filter(
        "a", [s for s in segments if isinstance(s, AudioSegment)])
    command.append_normalisation_filter()
    command.append_concat_filter(
        "v", [s for s in segments if isinstance(s, VideoSegment)])
    command.append_output_options([output])
    globals.log.debug("{fn}(): {c}".format(fn=fn, c=command))
    command.run()


def cleanup(segments):
    """Clean up generated temporary files."""
    globals.log.info("Cleaning up...")
    for s in segments:
        s.delete_temp_files()


def main():
    fn = "main"
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: {p}: %(message)s".format(p=globals.PROGRAM))
    
    args = parse_command_line()
    check_arguments(args)
    
    config = get_configuration(args)
    
    segments = process_input_streams(config)
    globals.log.debug("{fn}(): audio segments = {a}".format(
        fn=fn, a=[s for s in segments if isinstance(s, AudioSegment)]))
    globals.log.debug("{fn}(): audio segments = {v}".format(
        fn=fn, v=[s for s in segments if isinstance(s, VideoSegment)]))
    
    audio_duration = sum([s.get_duration() for s in segments
                          if isinstance(s, AudioSegment)])
    video_duration = sum([s.get_duration() for s in segments
                          if isinstance(s, VideoSegment)])
    globals.log.debug("{fn}(): audio duration = "
                      "{a}".format(fn=fn, a=audio_duration))
    globals.log.debug("{fn}(): video duration = "
                      "{v}".format(fn=fn, v=video_duration))
    
    if (audio_duration != video_duration):
        globals.log.warning("total video duration ({v}s) doesn't match "
                    "total audio duration "
                    "({a}s)".format(v=video_duration, a=audio_duration))
    
    # Set up frame segments that refer to the previous segment.
    for f in [s for s in segments if isinstance(s, FrameSegment)]:
        globals.log.debug("{fn}(): frame (before) = {b}".format(fn=fn, b=f))
        if (f.input_file == "^"):
            if (f.segment_number > 0):
                prev = segments[f.segment_number - 1]
                globals.log.debug("{fn}(): prev = {p}".format(fn=fn, p=prev))
                prev.generate_temp_file(args.output)
                f.use_frame(prev.generate_last_frame(args.output))
                globals.log.debug("{fn}(): frame (after) = "
                                  "{a}".format(fn=fn, a=f))
            else:
                globals.log.error("frame segment {s} is attempting to use the last frame "
                          "of a non-existent previous "
                          "segment".format(s=f.segment_number))
                sys.exit(1)
    
    globals.log.debug("{fn}(): input files = "
                      "{i}".format(fn=fn, i=Segment.input_files()))
    
    try:
        render_podcast(segments, args.output)
        if (not args.keep):
            cleanup(segments)
    except (KeyboardInterrupt):
        pass


if (__name__ == "__main__"):
    main()
