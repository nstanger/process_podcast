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
from progress_bar import (ProgressBar)
from segment import (Segment, AudioSegment, VideoSegment, FrameSegment)
from shell_command import (FFprobeCommand, FFmpegConcatCommand)


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
            "(note: .mov seems generally best)",
        epilog="Default input files can be specified using either of "
            "--audio or --video. If neither of these are specified, "
            "then you must supply a configuration file using --config. "
            "(Of course, you can always supply a configuration file "
            "regardless.)\n\n"
            "Input streams can be taken from the same input file.\n\n"
            "If no segments are specified, the entire input stream is "
            "processed as one segment. The number and duration of segments "
            "can differ, but the total duration across all input streams "
            "should ideally be the same.")
    
    parser.set_defaults(audio_stream_number=None, video_stream_number=None)

    parser.add_argument(
        "output",
        help="name of the output file (note: .mov is best)")
    
    parser.add_argument(
        "--audio", "-a", metavar="FILE[:STREAM]", action=InputStreamAction,
        help="File name for the default audio input stream (can be the "
            "same as for other input streams). You can optionally specify "
            "the default audio stream number to use if the file contains "
            "more than one (this can be overidden in a configuration "
            "file). If you don't specify a stream number, it defaults "
            "to 0 (i.e., the first audio stream in the file).")
    
    parser.add_argument(
        "--video", "-v", metavar="FILE[:STREAM]", action=InputStreamAction,
        help="File name for the default video input stream (can be the "
            "same as for other input streams). You can optionally specify "
            "the default video stream number to use if the file contains "
            "more than one (this can be overidden in a configuration "
            "file). If you don't specify a stream number, it defaults "
            "to 0 (i.e., the first video stream in the file).")
    
    parser.add_argument(
        "--configuration", "--config", "-c", dest="config", metavar="FILE",
        help="File name for the podcast segment configuration (plain text). "
            "See config_help.md details on the file "
            "format.".format(p=globals.PROGRAM))
    
    parser.add_argument(
        "--input-prefix", "-p", dest="prefix", metavar="PATH", default="",
        help="Path to be prefixed to all INPUT files. This includes the "
            "configuration file, if applicable, and any files specified "
            "within the configuration file.")
    
    parser.add_argument(
        "--debug", "-d", action="store_true",
        help="Print debugging output (overrides --quiet).")
    
    parser.add_argument(
        "--keep", "-k", action="store_true",
        help="Don't delete any generated temporary files.")
    
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Mute all console output (overridden by --debug).")

    args = parser.parse_args()
    
    return args


def check_arguments(args):
    """Sanity check the command line arguments."""
    fn = "check_arguments"
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
    
    # Prepend input files with --input-prefix where applicable.
    # Handily, if prefix is "", os.path.join() leaves the original
    # path unchanged.
    args.audio, args.video, args.config = map(
        lambda f: os.path.join(args.prefix, f) if f else f,
        [args.audio, args.video, args.config])


def get_configuration(args):
    """Load podcast configuration."""
    # Fill in missing file names for default input streams.
    fn = "get_configuration"
    # These types can have default input files and streams.
    type_mapping = {
        "audio": {"file": args.audio, "stream": args.audio_stream_number},
        "video": {"file": args.video, "stream": args.video_stream_number}}
    globals.log.info("Processing configuration...")
    if (args.config):
        config = parse_configuration_file(args.config)
        
        # Check that applicable default input streams have been specified.
        for i, c in enumerate(config):
            type = c["type"]
            
            # Add prefix to filename, if applicable.
            if c["filename"]:
                config[i]["filename"] = os.path.join(
                    args.prefix, config[i]["filename"])
            
            if (type in type_mapping):
                default_file = type_mapping[type]["file"]
                default_stream = type_mapping[type]["stream"]
                error_string = ("attempting to use default {s} input file, "
                    "but --{s} hasn't been specified".format(s=type))
            else:
                default_file = None
                default_stream = 0
                error_string = ("attempting to use a default input file, "
                    "but the {s} type doesn't support this".format(s=type))

            # No filename in configuration.
            if (not c["filename"]):
                if (default_file):
                    config[i]["filename"] = default_file
                # No filename on command line either.
                else:
                    globals.log.error(error_string)
                    sys.exit(1)
            
            # No stream number in configuration. Note: 0 is a valid
            # stream number, so explicitly check for None.
            if (c["num"] is None):
                # Assume 0 if no stream on command line either.
                if (default_stream is None):
                    config[i]["num"] = 0
                else:
                    config[i]["num"] = default_stream
    
    # No configuration file.
    else:
        conf_list = []
        for m in type_mapping:
            default_file = type_mapping[m]["file"]
            default_stream = type_mapping[m]["stream"]
            if (default_file and default_stream is not None):
                conf_list += ["[{type}:{file}:{stream}]".format(
                    type=m, file=default_file, stream=default_stream)]
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
    globals.log.debug("{fn}(): punch in = {i}".format(fn=fn, i=punch_in))
    globals.log.debug("{fn}(): punch out = {o}".format(fn=fn, o=punch_out))
    globals.log.debug("{fn}(): num = {n}".format(fn=fn, n=num))
    
    if (type == "audio"):
        return AudioSegment(file=filename, punch_in=punch_in,
                            punch_out=punch_out, input_stream=num)
    elif (type == "video"):
        return VideoSegment(file=filename, punch_in=punch_in,
                            punch_out=punch_out, input_stream=num)
    elif (type == "frame"):
        return FrameSegment(file=filename, punch_in=punch_in,
                            punch_out=punch_out, frame_number=num)
    else:
        return None


def process_timestamp_pair(args, times):
    """Constructs timedelta instances from a pair of config timestamps."""
    fn = "process_timestamp_pair"
    globals.log.debug("{fn}(): times[0] = {t}".format(fn=fn, t=times[0]))
    globals.log.debug("{fn}(): times[1] = {t}".format(fn=fn, t=times[1]))
    
    # If the first item in the timestamp list in the configuration file
    # is a filename, the parser inserts a zero timestamp before it. We
    # can therefore guarantee that the first item of the pair will
    # always be a timestamp.
    t0 = datetime.timedelta(
        hours=times[0]["hh"], minutes=times[0]["mm"],
        seconds=times[0]["ss"], milliseconds=times[0]["ms"])
    if (times[1]):
        if (len(times[1]) == 1): # filename
            t1 = t0 + get_file_duration(
                os.path.join(args.prefix, times[1]["filename"]))
        elif (len(times[1]) == 4): # normal timestamp
            t1 = datetime.timedelta(
                hours=times[1]["hh"], minutes=times[1]["mm"],
                seconds=times[1]["ss"], milliseconds=times[1]["ms"])
        else:
            globals.log.error("{fn}():unreadable timestamp {t}".format(
                fn=fn, t=times[1]))
            t1 = None
    else:
        t1 = None
    
    globals.log.debug("{fn}(): t0 = {t}".format(fn=fn, t=t0))
    globals.log.debug("{fn}(): t1 = {t}".format(fn=fn, t=t1))
    return t0, t1


def process_time_list(args, type, filename, num, time_list):
    """Process an audio or video stream and build a list of segments."""
    fn = "process_time_list"
    if (os.path.exists(filename) and type in ["audio", "video"]):
        stream_duration = get_file_duration(filename)
    else:
        stream_duration = 0
    segments = []
    globals.log.debug("{fn}(): stream duration = {d}".format(
        fn=fn, d=stream_duration))
    
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
            punch_in, punch_out = process_timestamp_pair(args, t)
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
        punch_in, _ = process_timestamp_pair(args, [time_list[-1], None])
        punch_out = stream_duration - punch_in
        segments.append(make_new_segment(type, filename, punch_in,
                                         punch_out, num))
    return segments


def process_input_streams(args, config):
    """Process a list of stream specifications and build a list of segments."""
    fn = "process_input_streams"
    globals.log.info("Processing input streams...")
    segments = []
    for cnf in config:
        globals.log.debug("{fn}(): type = {t}".format(fn=fn, t=cnf["type"]))
        globals.log.debug(
            "{fn}(): filename = {f}".format(fn=fn, f=cnf["filename"]))
        globals.log.debug("{fn}(): num = {n}".format(fn=fn, n=cnf["num"]))
        globals.log.debug("{fn}(): times = {t}".format(fn=fn, t=cnf["times"]))
    
        segments += process_time_list(args, cnf["type"], cnf["filename"],
                                      cnf["num"], cnf["times"])  
    return segments


def process_frame_segments(args, segments):
    """Post-process frame segments to set frame images, etc."""
    fn = "process_frame_segments"
    globals.log.info("Processing frames...")
    frame_segments = [s for s in segments if isinstance(s, FrameSegment)]
    n = len(frame_segments)
    progress = ProgressBar(max_value=n, quiet=args.quiet or args.debug)
    for i, f in enumerate(frame_segments):
        progress.update(i)
        globals.log.debug("{fn}(): frame (before) = {b}".format(fn=fn, b=f))
        # Frame segments that use a frame from the previous segment.
        if (f.input_file == "^"):
            if (f.segment_number > 0):
                prev = segments[f.segment_number - 1]
                globals.log.debug("{fn}(): prev = {p}".format(fn=fn, p=prev))
                prev.generate_temp_file(args.output)
                f.use_frame(prev.generate_frame(f.frame_number, args.output))
            else:
                globals.log.error(
                    "frame segment {s} is attempting to use the last frame "
                    "of a non-existent previous "
                    "segment".format(s=f.segment_number))
                sys.exit(1)
        # Frame segments whose frame comes from a PDF file.
        else:
            _, suffix = os.path.splitext(f.input_file)
            if (suffix.lower() == ".pdf"):
                f.use_frame(f.generate_temp_file(args.output))
            else:
                globals.log.error(
                    'unexpected input file type "{s}" for frame segment '
                    "{f}".format(s=suffix, f=f.segment_number))
                sys.exit(1)
        globals.log.debug("{fn}(): frame (after) = ""{a}".format(fn=fn, a=f))
    progress.finish()


def render_podcast(args, audio_segments, video_segments, output, duration):
    """Stitch together the various input components into the final podcast."""
    fn = "render_podcast"
    globals.log.info("Rendering final podcast...")
    command = FFmpegConcatCommand(has_audio=len(audio_segments) > 0,
                                  has_video=len(video_segments) > 0,
                                  max_progress=duration,
                                  quiet=args.quiet and not args.debug)
    input_files = Segment.input_files()
    for f in input_files:
        if (input_files[f]):
            command.append_input_options(input_files[f])
        command.append_input_options(["-i", f])
    for s in (audio_segments + video_segments):
        command.append_filter(s.trim_filter())
    command.append_concat_filter("a", [s for s in audio_segments])
    command.append_normalisation_filter()
    command.append_concat_filter("v", [s for s in video_segments])
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
    
    try:
        args = parse_command_line()
        check_arguments(args)
    
        config = get_configuration(args)
    
        segments = process_input_streams(args, config)
        globals.log.debug("{fn}(): audio segments = {a}".format(
            fn=fn, a=[s for s in segments if isinstance(s, AudioSegment)]))
        globals.log.debug("{fn}(): video segments = {v}".format(
            fn=fn, v=[s for s in segments if isinstance(s, VideoSegment)]))
    
        audio_segments = [s for s in segments if isinstance(s, AudioSegment)]
        video_segments = [s for s in segments if isinstance(s, VideoSegment)]
    
        audio_duration = sum([s.get_duration() for s in audio_segments])
        video_duration = sum([s.get_duration() for s in video_segments])
        globals.log.debug("{fn}(): audio duration = "
                          "{a}".format(fn=fn, a=audio_duration))
        globals.log.debug("{fn}(): video duration = "
                          "{v}".format(fn=fn, v=video_duration))
    
        if (len(audio_segments) and len(video_segments)):
            if (audio_duration != video_duration):
                globals.log.warning("total video duration ({v}s) doesn't match "
                            "total audio duration "
                            "({a}s)".format(v=video_duration, a=audio_duration))
    
        process_frame_segments(args, segments)
    
        globals.log.debug("{fn}(): input files = "
                          "{i}".format(fn=fn, i=Segment.input_files()))
    
        render_podcast(args, audio_segments, video_segments, args.output,
                       max(audio_duration, video_duration))

        if (not args.keep):
            cleanup(segments)
    
    except (KeyboardInterrupt):
        pass


if (__name__ == "__main__"):
    main()
