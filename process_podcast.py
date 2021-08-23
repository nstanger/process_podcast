#!/usr/bin/env python3

import argparse
import datetime
import logging
from pathlib import Path, PurePath
import sys

from pyparsing import ParseResults

import globals
from config_parser import (
    parse_configuration_file, parse_configuration_string
)
from progress_bar import ProgressBar
from segment import (
    Segment, AudioSegment, VideoSegment,
    FrameSegment, SegmentError
)
from shell_command import FFprobeCommand, FFmpegConcatCommand


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
        "--copy-audio", dest="process_audio", action="store_false",
        default=True,
        help="Disable additional processing of the source audio. The audio "
            "will still be re-encoded using the specified audio codec "
            "because the concatenation filter requires it, but extra "
            "processing such as reduction of channels or normalisation "
            "will not be carried out. (Implies --no-normalise.)")
    
    parser.add_argument(
        "--copy-video", dest="process_video", action="store_false",
        default=True,
        help="Disable additional processing of the source video. The video "
            "will still be re-encoded using the specified video codec "
            "because the concatenation filter requires it, but extra "
            "processing such as remapping of colours will not be "
            "carried out.")
    
    parser.add_argument(
        "--no-normalise", dest="normalise", action="store_false",
        default=True,
        help="Disable normalisation of the source audio level (implied by "
            "--copy-audio).")
    
    parser.add_argument(
        "--audio-codec", dest="audio_codec", metavar="CODEC",
        default="pcm_s16le",
        help="Specify ffmpeg audio codec for output (default pcm_s16le). "
            "See the output of ffmpeg -codecs for possible codecs.")
    
    parser.add_argument(
        "--video-codec", dest="video_codec", metavar="CODEC", default="h264",
        help="Specify ffmpeg video codec for output (default h264). "
            "See the output of ffmpeg -codecs for possible codecs.")
    
    parser.add_argument(
        "--input-prefix", "-i", dest="prefix", metavar="PATH", default=".",
        help="Path to be prefixed to all INPUT files. This includes the "
            "configuration file, if applicable, and any files specified "
            "within the configuration file. Input files that already "
            "include the input prefix will not have it added again.")
    
    parser.add_argument(
        "--preview", "-p", metavar="RATE", nargs="?", const="1",
        help="Generate a preview of the podcast by only rendering a "
            "subset of the video frames. RATE is the number of frames "
            "per second to render (default 1 fps). You can specify "
            "fractions (e.g., 1/10 for one frame every 10 seconds). "
            'NOTE: if you get a "too few arguments" error when using '
            "this option, you've probably not provided an fps value and "
            "placed the option just before the output filename. "
            "Either move --preview earlier in the option list, add "
            'a "--" between it and the output filename, or provide a '
            "fps value.")
    
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


def prefix_path(prefix, path):
    """Prepend prefix to path, unless path already starts with prefix"""
    assert(prefix is not None)
    if not path:
        return None
    elif path == "." or path.startswith(prefix):
        return path
    else:
        return Path(prefix, path)


def check_arguments(args):
    """Sanity check the command line arguments."""
    fn = "check_arguments"
    # Prepend input files with --input-prefix where applicable.
    args.audio, args.video, args.config = map(
        prefix_path, [args.prefix] * 3, [args.audio, args.video, args.config])

    if args.quiet:
        globals.log.setLevel(logging.WARNING)
    
    # --copy-audio implies --no-normalise.
    if not args.process_audio:
        args.normalise = False
        
    # --debug overrides --quiet.
    if args.debug:
        globals.log.setLevel(logging.DEBUG)
        globals.log.debug("{fn}(): args = {a}".format(fn=fn, a=args))
    
    # Must specify at least one of --audio, --video, --config.
    if not any([args.audio, args.video, args.config]):
        globals.log.error("must specify at least one of --audio, --video, "
                          "or --config")
        sys.exit(1)
    
    if not Path(args.prefix).exists():
        globals.log.error('input prefix "{p}" does not '
                          "exist".format(p=args.prefix))
        sys.exit(1)
    

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
            if c["filename"] and (c["filename"] != "^"):
                config[i]["filename"] = prefix_path(args.prefix,
                                                    config[i]["filename"])
            
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
    fn = "get_file_duration"
    command = FFprobeCommand([file])
    globals.log.debug("{fn}(): {cmd}".format(fn=fn, cmd=command))
    # Only consider the first stream. If it's the only stream in the
    # file, great; otherwise it seems reasonable to assume that all
    # streams in the same file will have the same duration.
    ss, ms = command.get_entries(
        section="format", find_list=["duration"])[0].split(".")
    ms = ms[:3].ljust(3, "0")
    globals.log.debug("{fn}(): ss = {ss}, ms = {ms}".format(fn=fn, ss=ss,
                                                            ms=ms))
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
                prefix_path(args.prefix, times[1]["filename"]))
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
    if (Path(filename).exists() and type in ["audio", "video"]):
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
        globals.log.debug("{fn}(): odd number of timestamps".format(fn=fn))
        punch_in, _ = process_timestamp_pair(args, [time_list[-1], None])
        punch_out = stream_duration
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


def smallest_video_dimensions(args, segments):
    """Compute the smallest frame dimensions across all video inputs."""
    fn = "smallest_video_dimensions"
    width = 2048
    height = 1536
    for s in segments:
        if isinstance(s, FrameSegment):
            continue
        command = FFprobeCommand([s.input_file])
        globals.log.debug("{fn}(): {cmd}".format(fn=fn, cmd=command))
        w, h = command.get_entries(find_list=["width", "height"])
        if (w * h) < (width * height):
            width, height = w, h
    return width, height


def process_frame_segments(args, segments, width, height):
    """Post-process frame segments to set frame images, etc."""
    fn = "process_frame_segments"
    globals.log.info("Processing frames...")
    frame_segments = [s for s in segments if isinstance(s, FrameSegment)]
    n = len(frame_segments)
    globals.log.debug("{fn}(): num frames = {n}".format(fn=fn, n=n))
    progress = ProgressBar(max_value=n,
                           quiet=args.quiet or args.debug or n == 0)
    progress.update(0)
    for i, f in enumerate(frame_segments):
        try:
            globals.log.debug(
                "{fn}(): frame (before) = {b}".format(fn=fn, b=f))
            # Frame segments that use a frame from the previous segment.
            if (f.input_file == "^"):
                if (f.segment_number > 0):
                    prev = segments[f.segment_number - 1]
                    globals.log.debug(
                        "{fn}(): prev = {p}".format(fn=fn, p=prev))
                    prev.generate_temp_file(args.output, width=width,
                                            height=height)
                    f.use_frame(
                        prev.generate_frame(f.frame_number, args.output,
                                            width=width, height=height))
                else:
                    globals.log.error(
                        "frame segment {s} is attempting to use the last "
                        "frame of a non-existent previous "
                        "segment".format(s=f.segment_number))
                    sys.exit(1)
            # Frame segments whose frame comes from a PDF file.
            else:
                suffix = PurePath(f.input_file).suffix
                if (suffix.lower() == ".pdf"):
                    f.use_frame(f.generate_temp_file(args.output, width=width,
                                            height=height))
                else:
                    globals.log.error(
                        'unexpected input file type "{s}" for frame segment '
                        "{f}".format(s=suffix, f=f.segment_number))
                    sys.exit(1)
            progress.update(i)
            globals.log.debug("{fn}(): frame (after) = ""{a}".format(fn=fn, a=f))
        except SegmentError as e:
            progress.finish()
            globals.log.exception(e)
            sys.exit(1)
    else:
        progress.finish()


def render_podcast(args, audio_segments, video_segments, output, duration):
    """Stitch together the various input components into the final podcast."""
    fn = "render_podcast"
    globals.log.info("Rendering final podcast...")
    command = FFmpegConcatCommand(has_audio=len(audio_segments) > 0,
                                  has_video=len(video_segments) > 0,
                                  max_progress=duration,
                                  quiet=args.quiet and not args.debug,
                                  process_audio=args.process_audio,
                                  process_video=args.process_video,
                                  audio_codec=args.audio_codec,
                                  video_codec=args.video_codec)
    input_files = Segment.input_files()
    for f in input_files:
        if (input_files[f]):
            command.append_input_options(input_files[f])
        command.append_input_options(["-i", f])
    for s in (audio_segments + video_segments):
        command.append_filter(s.trim_filter())
    command.append_concat_filter("a", [s for s in audio_segments])
    if (args.normalise):
        command.append_normalisation_filter()
    command.append_concat_filter("v", [s for s in video_segments])
    if args.preview:
        globals.log.info("PREVIEW MODE: {fps} fps".format(fps=args.preview))
        command.append_output_options(["-r", args.preview])
    command.append_output_options([output])
    globals.log.debug("{fn}(): {c}".format(fn=fn, c=command))
    if (command.run() != 0):
        globals.log.error("Failed to render final podcast")


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
    segments = None
    
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
        
        width, height = smallest_video_dimensions(args, video_segments)
        globals.log.debug("{fn}(): width = {w}, height = "
                          "{h}".format(fn=fn, w=width, h=height))
        
        process_frame_segments(args, segments, width, height)
    
        globals.log.debug("{fn}(): input files = "
                          "{i}".format(fn=fn, i=Segment.input_files()))
    
        render_podcast(args, audio_segments, video_segments, args.output,
                       max(audio_duration, video_duration))

    except (KeyboardInterrupt):
        pass
    finally:
        if segments and not args.keep:
            cleanup(segments)


if (__name__ == "__main__"):
    assert sys.version_info >= (3, 5)
    main()
