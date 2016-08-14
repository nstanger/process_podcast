#!/usr/bin/env python

import argparse
import datetime
import distutils.spawn
import itertools
import logging
import os
import os.path
import re
import subprocess
import sys
import textwrap
from collections import OrderedDict
from decimal import *

from pyparsing import ParseResults
from parse_podcast_config import (
    parse_configuration_file, parse_configuration_string)


PROGRAM = "process_lectorial_capture"


class ShellCommand(object):
    """A shell command.
    
    _executable contains the full path to the relevant executable.
    
    _base_options is a list of standard general options for this
    command.
    """
    _executable = ""
    _base_options = []
    
    def __init__(self, options=[]):
        self.options = options
    
    def __repr__(self):
        return "<{cls}: {cmd}>".format(
            cls=self.__class__.__name__,
            cmd=" ".join(self.command_items(True)))
    
    def command_items(self, debug=False):
        """Return the list of items representing the command."""
        return ([self._executable] + self._base_options + self.options)
    
    def run(self):
        """Execute the command in a subprocess."""
        return subprocess.call(self.command_items())
    
    def get_output(self):
        """Execute the command in a subprocess and return the output."""
        return subprocess.check_output(self.command_items())


class ConvertCommand(ShellCommand):
    """An ImageMagick convert command."""
    _executable = distutils.spawn.find_executable("convert")
    _base_options = ["-scale", "2048x1536", "-density", "600"]
    

class FFprobeCommand(ShellCommand):
    """An ffprobe shell command."""
    _executable = distutils.spawn.find_executable("ffprobe")
    _base_options = ["-loglevel", "error"]

    
class FFmpegCommand(ShellCommand):
    """A "simple" ffmpeg shell command."""
    _executable = distutils.spawn.find_executable("ffmpeg")
    _base_options = ["-y", "-loglevel", "error", "-nostdin"]

    def __init__(self, input_options=[], output_options=[]):
        self.input_options = input_options
        self.output_options = output_options
    
    def append_input_options(self, items=[]):
        """Add a list of items to the end of the input options."""
        self.input_options += items
    
    def prepend_input_options(self, items=[]):
        """Add a list of items at the front of the input options."""
        self.input_options = items + self.input_options
    
    def append_output_options(self, items=[]):
        """Add a list of items to the end of the output options."""
        self.output_options += items
    
    def prepend_output_options(self, items=[]):
        """Add a list of items at the front of the output options."""
        self.output_options = items + self.output_options
    
    def command_items(self, debug=False):
        """Return the list of items representing the command."""
        return ([self._executable] + self._base_options +
                self.input_options + self.output_options)
        

class FFmpegConcatCommand(FFmpegCommand):
    """An ffmpeg shell command with a complex concat filter."""
    def __init__(self, input_opts=[], output_opts=[], num_streams=0):
        super(FFmpegConcatCommand, self).__init__(input_opts, output_opts)
        self.prepend_output_options(["-codec:a", "pcm_s16le",
                                     "-ac", "1",
                                     "-codec:v", "h264",
                                     "-map", "[vconc]",
                                     "-map", "[anorm]"])
        self.filters = []
    
    def append_filter(self, filter):
        """Append a filter to the filters list."""
        self.filters.append(filter)
        
    def append_normalisation_filter(self):
        """Append a normalisation audio filter to the complex filter."""
        self.append_filter("[aconc] dynaudnorm=r=0.25:f=10:b=y [anorm]")
    
    def append_concat_filter(self, type, segments=[]):
        """Append a concat filter to the filters list"""
        self.append_filter(
            "{inspecs} concat=n={n}:v={v}:a={a} [{t}conc]".format(
                inspecs=" ".join([s.output_stream_specifier()
                                  for s in segments]),
                n=len(segments), v=int(type == "v"),
                a=int(type == "a"), t=type))
        
    def build_complex_filter(self):
        """Build the complete complex filter.
        
        Filters in the filtergraph are separated by ";".
        """
        return "{f}".format(f=";".join(self.filters))
    
    def command_items(self, debug=False):
        """Return the list of items representing the command."""
        complex_filter = self.build_complex_filter()
        output_opts = self.output_options
        if (debug):
            # Wrap the output streams and the entire complex filter
            # in 'single quotes', so that we can copy and paste the
            # command string directly into the shell for testing.
            complex_filter = "'{f}'".format(f=complex_filter)
            output_opts = [re.sub(r"\[(\w+)\]", r"'[\1]'", s)
                           for s in self.output_options]
        return ([self._executable] + self._base_options + self.input_options +
                ["-filter_complex", complex_filter] + output_opts)
    

class Segment(object):
    """A segment within the podcast.
    
    A segment has an input file, and a punch-in and punch-out
    point (both in seconds).
    """
    _new_segment_num = itertools.count().next
    _input_files = OrderedDict()
    _TYPE = ""
    _TRIM = ""
    _SETPTS = ""
    
    @staticmethod
    def input_files():
        return Segment._input_files
    
    @staticmethod
    def _rename_input_file(old, new):
        tmp = OrderedDict()
        for f in Segment._input_files:
            if (f == old):
                tmp[new] = Segment._input_files[f]
            else:
                tmp[f] = Segment._input_files[f]
        Segment._input_files = tmp
    
    def __init__(self, file="", punch_in=0, punch_out=0, input_stream=0):
        self.segment_number = self.__class__._new_segment_num()
        self.input_file = file
        self.punch_in = punch_in
        self.punch_out = punch_out
        self.input_stream = input_stream
        self._temp_file = ""
        self._temp_suffix = "mov"
        
        if (file not in self.__class__._input_files):
            self.__class__._input_files[file] = None
        
        self._input_options = ["-ss", str(self.punch_in.total_seconds()),
                               "-t", str(self.get_duration()),
                               "-i", self.input_file]
        self._output_options = []
            
    def __repr__(self):
        return('<{c} {n}: file "{f}", in {i}, out '
               '{o}>'.format(c=self.__class__.__name__,
                             n=self.segment_number,
                             t=self._TYPE,
                             f=self.input_file,
                             i=self.punch_in,
                             o=self.punch_out))
    
    def get_duration(self):
        """Return the duration of the segment in seconds."""
        return (self.punch_out - self.punch_in).total_seconds()
    
    def generate_temp_file(self, output):
        """Compile the segment from the original source file(s)."""
        self._temp_file = os.path.extsep.join(
            ["temp_{t}_{o}_{n:03d}".format(t=self._TYPE,
                                           o=os.path.splitext(output)[0],
                                           n=self.segment_number),
             self._temp_suffix])
        command = FFmpegCommand(
            input_options=self._input_options + ["-codec", "copy"],
            output_options=self._output_options + [self._temp_file])
        logging.getLogger(PROGRAM).debug(command)
        command.run()
    
    def temp_file(self):
        """Return the temporary file associated with the segment."""
        return self._temp_file
    
    def delete_temp_files(self):
        """Delete the temporary file(s) associated with the segment."""
        if (self._temp_file):
            os.remove(self._temp_file)
    
    def input_stream_specifier(self):
        """Return the segment's ffmpeg stream input specifier."""
        return "[{n}:{t}]".format(
            n=self.__class__._input_files.keys().index(self.input_file),
            t=self._TYPE[0] if self._TYPE else "")
        
    def output_stream_specifier(self):
        """Return the segment's ffmpeg audio stream output specifier."""
        return "[{t}{n}]".format(t=self._TYPE[0] if self._TYPE else "",
                                 n=self.segment_number)
    
    def trim_filter(self):
        """Return an FFMPEG trim filter for this segment."""
        return ("{inspec} "
                "{trim}=start={pi}:duration={po},{setpts}=PTS-STARTPTS "
                "{outspec}".format(
                    inspec=self.input_stream_specifier(),
                    trim=self._TRIM, setpts=self._SETPTS,
                    pi=self.punch_in.total_seconds(),
                    po=self.get_duration(),
                    outspec=self.output_stream_specifier()))


class AudioSegment(Segment):
    """A segment of an audio input stream."""
    _TYPE = "audio"
    _TRIM = "atrim"
    _SETPTS = "asetpts"

    def __init__(self, file="", punch_in=0, punch_out=0, input_stream=0):
        super(AudioSegment, self).__init__(file, punch_in, punch_out,
                                           input_stream)
        self._temp_suffix = "wav"
        self._output_options = ["-ac", "1",
                                "-map", "{n}:a".format(n=self.input_stream)]
    

class VideoSegment(Segment):
    """A segment of a video input stream."""
    _TYPE = "video"
    _TRIM = "trim"
    _SETPTS = "setpts"

    def __init__(self, file="", punch_in=0, punch_out=0, input_stream=0):
        super(VideoSegment, self).__init__(file, punch_in, punch_out,
                                           input_stream)
        self._output_options = ["-map", "{n}:v".format(n=self.input_stream)]
        self._temp_frame_file = ""
    
    def get_last_frame_number(self):
        """Calculate frame number of segment's last frame using ffprobe."""
        log = logging.getLogger(PROGRAM)
        if (self._temp_file):
            self._temp_frame_file = "__{f}".format(f=self._temp_file)
        
            # To speed things up, grab up to the last 5 seconds of the
            # segment's temporary file, as we otherwise have to scan the
            # entire temporary file to find the last frame, which can
            # take a while.
            command = FFmpegCommand(
                input_options=["-ss", str(max(self.get_duration() - 5, 0)),
                               "-i", self._temp_file],
                output_options=["-codec:v", "copy",
                                "-map", "0:v",
                                self._temp_frame_file])
            log.debug(command)
            command.run()
            command = FFprobeCommand(
                options=["-select_streams", "v",
                         "-show_entries", "stream=nb_frames",
                         "-print_format", "default=noprint_wrappers=1:nokey=1",
                         self._temp_frame_file])
            log.debug(command)
            return int(command.get_output().strip()) - 1
        else:
            return -1
    
    def generate_last_frame(self, output):
        """Create a JPEG file from the last frame of the segment."""
        temp_frame = os.path.extsep.join(
            ["temp_{t}_{f}_{n:03d}".format(t=self._TYPE,
                                           f=os.path.splitext(output)[0],
                                           n=self.segment_number),
             "jpg"])
        num = self.get_last_frame_number()
        command = FFmpegCommand(
            input_options=["-i", self._temp_frame_file],
            output_options=["-filter:v", "select='eq(n, {n})'".format(n=num),
                            "-frames:v", "1",
                            "-f", "image2",
                            "-map", "0:v",
                            temp_frame])
        logging.getLogger(PROGRAM).debug(command)
        if (command.run() == 0):
            os.remove(self._temp_frame_file)
            return temp_frame
        else:
            return None
    

class FrameSegment(VideoSegment):
    """A video segment derived from a single still frame."""
    _TYPE = "frame"
    
    def __init__(self, file="", punch_in=0, punch_out=0, input_stream=0):
        super(FrameSegment, self).__init__(file, punch_in, punch_out,
                                           input_stream)
        self._input_options = ["-loop", "1",
                               "-t", str(self.get_duration()),
                               "-i", self.input_file]
        self.__class__._input_files[file] = self._input_options[:4]
    
    def generate_temp_file(self, output):
        """Compile the segment from the original source file(s)."""
        self._temp_file = os.path.extsep.join(
            ["temp_{t}_{o}_{n:03d}".format(t=self._TYPE,
                                           o=os.path.splitext(output)[0],
                                           n=self.segment_number),
             "jpg"])
        command = ConvertCommand(
            options=["{f}[{n}]".format(f=self.input_file,
                                       n=self.input_stream),
                     self._temp_file])
        logging.getLogger(PROGRAM).debug(command)
        command.run()
    
    def use_frame(self, frame):
        """Set the image to use for generating the frame video."""
        self.__class__._rename_input_file(self.input_file, frame)
        self.input_file = frame
        self._input_options = ["-loop", "1",
                               "-t", str(self.get_duration()),
                               "-i", self.input_file]
        self.__class__._input_files[frame] = self._input_options[:4]
        
    def input_stream_specifier(self):
        """Return the segment's ffmpeg stream input specifier."""
        return "[{n}:v]".format(
            n=self.__class__._input_files.keys().index(self.input_file))
        
    def output_stream_specifier(self):
        """Return the segment's ffmpeg audio stream output specifier."""
        return self.input_stream_specifier()
    
    def trim_filter(self):
        """Return an FFMPEG trim filter for this segment."""
        return ""
    
    def delete_temp_files(self):
        """Delete the temporary file(s) associated with the scene."""
        if (self.input_file):
            os.remove(self.input_file)
        super(FrameSegment, self).delete_temp_files()


def parse_command_line():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        usage="%(prog)s [options] <output>",
        description="where: <output> is the name of the output file "
            "(note: .mov is generally best)",
        epilog="Default input streams can be specified using any of "
            "--audio, --video, or --frame. If none of these are specified, "
            "then you must supply a configuration file using --config.\n\n"
            "Input streams can be taken from the same input file.\n\n"
            "If no segments are specified, the entire input stream is "
            "processed as one segment. The number and duration of segments "
            "can differ, but all input streams must have the same the total "
            "length.")
    
    parser.add_argument(
        "output",
        help="name of the output file (note: .mov is best)")
    
    parser.add_argument(
        "--audio", "-a", metavar="FILE",
        help="File name for the default audio input stream (can be the "
            "same as other input streams). Only the first audio stream "
            "in the file is read unless you specify otherwise in a "
            "configuration file.")
    
    parser.add_argument(
        "--configuration", "--config", "-c", dest="config", metavar="FILE",
        help="File name for the podcast segment configuration (plain text). "
            "Run {p} --help-config for details on the file "
            "format.".format(p=PROGRAM))
    
    parser.add_argument(
        "--debug", "-d", action="store_true",
        help="Print debugging output (overrides --quiet).")
    
    # Does this make sense as an option? It's a special case of video,
    # and probably makes more sense in the context of a config file
    # anyway. Howe does one specify last frame of previous segment
    # from the command line?
    parser.add_argument(
        "--frame", "-f", metavar="FILE",
        help="File name for the default frame input stream (can be the "
            "same as other input streams). Only the first video stream "
            "(where applicable) in the file is read unless you specify "
            "otherwise in a configuration file.")
    
    parser.add_argument(
        "--keep", "-k", action="store_true",
        help="Don't delete any generated temporary files.")
    
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Mute all console output (overridden by --debug).")

    parser.add_argument(
        "--video", "-v", metavar="FILE",
        help="File name for the default video input stream (can be the "
            "same as other input streams). Only the first video stream "
            "in the file is read unless you specify otherwise in a "
            "configuration file.")
    
    args = parser.parse_args()
    
    return args


def print_config_help():
    """Print details of the configuration file format."""
    print "Help is coming."
    sys.exit(0)


def check_arguments(args):
    """Sanity check the command line arguments."""
    log = logging.getLogger(PROGRAM)
    
#     if (args.help_config):
#         print_config_help()
    
    if (args.quiet):
        log.setLevel(logging.WARNING)
        
    # --debug overrides --quiet.
    if (args.debug):
        log.setLevel(logging.DEBUG)
        log.debug("check_arguments(): args = %s", args)
    
    # Must specify at least one of --audio, --video, --frame, --config.
    if (not any([args.audio, args.video, args.frame, args.config])):
        log.error("must specify at least one of --audio, --video, "
                  "--frame, or --config")
        sys.exit(1)
    

def get_configuration(args):
    log = logging.getLogger(PROGRAM)
    
    # Fill in missing file names for default input streams.
    file_mapping = {"audio": args.audio, "video": args.video,
                    "frame": args.frame}
    if (args.config):
        config = parse_configuration_file(args.config)
        # Check that applicable default input streams have been specified.
        for i, c in enumerate(config):
            if (not c["filename"]):
                if (file_mapping[c["type"]]):
                    config[i]["filename"] = file_mapping[c["type"]]
                else:
                    log.error(
                        "attempting to use default {s} input stream, but "
                        "--{s} hasn't been specified".format(s=c["type"]))
                    sys.exit(1)    
    else:
        conf_list = ["[{type}:{file}:0]".format(type=m, file=file_mapping[m])
                     for m in file_mapping if file_mapping[m]]
        log.debug("get_configuration(): default config = %s", conf_list)
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


def read_segments_from_file(segments_file):
    """Read a list of segment punch-in, punch-out point from a file."""
    segments = []
    with open(segments_file) as f:
        for line in f:
            segments.append(dict(zip(["in", "out"], line.split())))
    return segments


def make_new_segment(type, filename, punch_in, punch_out, num):
    """Make a new segment instance of the correct class."""
    log = logging.getLogger(PROGRAM)
    log.debug("make_new_segment(): type = %s", type)
    log.debug("make_new_segment(): filename = %s", filename)
    log.debug("make_new_segment(): punch in = %s", punch_in)
    log.debug("make_new_segment(): punch out = %s", punch_out)
    log.debug("make_new_segment(): num = %s", num)
    
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
    log = logging.getLogger(PROGRAM)
    log.debug("process_timestamp_pair(): t0 = {t0}".format(t0=times[0]))
    log.debug("process_timestamp_pair(): t1 = {t1}".format(t1=times[1]))
    
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
        log.error("unreadable timestamp {t}".format(t=times[1]))
    
    return t0, t1


def process_time_list(type, filename, num, time_list):
    """Process an audio or video stream and build a list of segments."""
    log = logging.getLogger(PROGRAM)
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
                log.warning("punch in ({i}s) and punch out ({o}s) times are "
                            "equal; no segment will be "
                            "generated".format(i=punch_in.total_seconds(),
                                               o=punch_out.total_seconds()))
                continue
            elif (punch_out < punch_in):
                log.error("punch out time ({i}s) falls before punch in time "
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
    log = logging.getLogger(PROGRAM)
    segments = []
    for cnf in config:
        log.debug("process_input_streams(): type = %s", cnf["type"])
        log.debug("process_input_streams(): filename = %s", cnf["filename"])
        log.debug("process_input_streams(): num = %s", cnf["num"])
        log.debug("process_input_streams(): times = %s", cnf["times"])
    
        segments += process_time_list(cnf["type"], cnf["filename"],
                                      cnf["num"], cnf["times"])  
    return segments



def concatenate_segments(segments, output):
    """Concatenate the temporary segment files into the final podcast."""
    log = logging.getLogger(PROGRAM)
    log.info("Concatenating final podcast...")
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
    log.debug(command)
    command.run()


def cleanup(segments):
    """Clean up generated temporary files."""
    logging.getLogger(PROGRAM).info("Cleaning up...")
    for s in segments:
        s.delete_temp_files()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: {p}: %(message)s".format(p=PROGRAM))
    log = logging.getLogger(PROGRAM)
    
    args = parse_command_line()
    check_arguments(args)
    
    config = get_configuration(args)
    
    segments = process_input_streams(config)
    log.debug([s for s in segments if isinstance(s, AudioSegment)])
    log.debug([s for s in segments if isinstance(s, VideoSegment)])
    
    audio_duration = sum([s.get_duration() for s in segments
                          if isinstance(s, AudioSegment)])
    video_duration = sum([s.get_duration() for s in segments
                          if isinstance(s, VideoSegment)])
    log.debug("main(): audio duration = {a}".format(a=audio_duration))
    log.debug("main(): video duration = {v}".format(v=video_duration))
    
    if (audio_duration != video_duration):
        log.warning("total video_duration ({v}s) doesn't match "
                    "total audio duration "
                    "({a}s)".format(v=video_duration, a=audio_duration))
    
    # Set up frame segments that refer to the previous segment.
    for f in [s for s in segments if isinstance(s, FrameSegment)]:
        log.debug(f)
        if (f.segment_number > 0):
            prev = segments[f.segment_number - 1]
            log.debug(prev)
            prev.generate_temp_file(args.output)
            f.use_frame(prev.generate_last_frame(args.output))
            log.debug(f)
        else:
            log.error("frame segment {s} is attempting to use the last frame "
                      "of a non-existent previous "
                      "segment".format(s=f.segment_number))
    
    print Segment.input_files()
    
    try:
        concatenate_segments(segments, args.output)
        if (not args.keep):
            cleanup(segments)
    except (KeyboardInterrupt):
        pass


if (__name__ == "__main__"):
    main()
