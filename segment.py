#!/usr/bin/env python

from collections import OrderedDict
import errno
import itertools
import logging
import os
import os.path

import globals
from shell_command import (ConvertCommand, FFprobeCommand, FFmpegCommand)


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
        fn = "generate_temp_file"
        self._temp_file = os.path.extsep.join(
            ["temp_{t}_{o}_{n:03d}".format(t=self._TYPE,
                                           o=os.path.splitext(output)[0],
                                           n=self.segment_number),
             self._temp_suffix])
        command = FFmpegCommand(
            input_options=self._input_options + ["-codec", "copy"],
            output_options=self._output_options + [self._temp_file])
        globals.log.debug("{cls}.{fn}(): {cmd}".format(
            cls=self.__class__.__name__, fn=fn, cmd=command))
        command.run()
    
    def temp_file(self):
        """Return the temporary file associated with the segment."""
        return self._temp_file
    
    def delete_temp_files(self):
        """Delete the temporary file(s) associated with the segment."""
        # Note: sometimes segments (especially frame segments) may
        # share the same temporary file. Just ignore the file not
        # found exception that occurs in these cases.
        if (self._temp_file):
            try:
                os.remove(self._temp_file)
            except OSError as e:
                if (e.errno != errno.ENOENT):
                    raise e
    
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
        fn = "get_last_frame_number"
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
            globals.log.debug("{cls}.{fn}(): {cmd}".format(
                cls=self.__class__.__name__, fn=fn, cmd=command))
            command.run()
            command = FFprobeCommand(
                options=["-select_streams", "v",
                         "-show_entries", "stream=nb_frames",
                         "-print_format", "default=noprint_wrappers=1:nokey=1",
                         self._temp_frame_file])
            globals.log.debug("{cls}.{fn}(): {cmd}".format(
                cls=self.__class__.__name__, fn=fn, cmd=command))
            return int(command.get_output().strip()) - 1
        else:
            return -1
    
    def generate_last_frame(self, output):
        """Create a JPEG file from the last frame of the segment."""
        fn = "generate_last_frame"
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
        globals.log.debug("{cls}.{fn}(): {cmd}".format(
            cls=self.__class__.__name__, fn=fn, cmd=command))
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
        fn = "generate_temp_file"
        self._temp_file = os.path.extsep.join(
            ["temp_{t}_{o}_{n:03d}".format(t=self._TYPE,
                                           o=os.path.splitext(output)[0],
                                           n=self.segment_number),
             "jpg"])
        command = ConvertCommand(
            options=["{f}[{n}]".format(f=self.input_file,
                                       n=self.input_stream),
                     self._temp_file])
        globals.log.debug("{cls}.{fn}(): {cmd}".format(
            cls=self.__class__.__name__, fn=fn, cmd=command))
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
        # Note: sometimes segments (especially frame segments) may
        # share the same temporary file. Just ignore the file not
        # found exception that occurs in these cases.
        if (self.input_file):
            try:
                os.remove(self.input_file)
            except OSError as e:
                if (e.errno != errno.ENOENT):
                    raise e
        super(FrameSegment, self).delete_temp_files()


if (__name__ == "__main__"):
    pass
