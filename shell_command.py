#!/usr/bin/env python

import datetime
import distutils.spawn
import json
import os.path
import re

import pexpect

from progress_bar import (ProgressBar)


class ShellCommand(object):
    """A shell command.
    
    _executable contains the full path to the relevant executable.
    
    _base_options is a list of standard general options for this
    command.
    """
    _executable = ""
    _base_options = []
    _expect_patterns = []
    
    @staticmethod
    def shellquote(s):
        """Quote a string so it can be safely pasted into the shell."""
        # Note: pipes/shlex.quote() only wraps '' around things,
        # it doesn't do things like \( \), which we also need.
        regexes = [re.compile(r"\("), re.compile(r"\)"),
                   re.compile(r"(\S+\s+[\S\s]+)"), 
                   re.compile(r"\[([^]]+)\]$")]
        substitutions = [r"\\(", r"\\)", r"'\1'", r"'[\1]'"]
        for sub in zip(regexes, substitutions):
            s = sub[0].sub(sub[1], s) if s else s
        return s
    
    def __init__(self, input_options=[], output_options=[], quiet=False):
        self.input_options = input_options
        self.output_options = output_options
        self.progress = None
        self.process = None
    
    def __repr__(self):
        return "<{cls}: {cmd}>".format(
            cls=self.__class__.__name__,
            cmd=self.command_string(quote=True))

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
    
    def executable_string(self, quote=False):
        """Return the executable as a string."""
        if quote:
            return ShellCommand.shellquote(self._executable)
        else:
            return self._executable
    
    def argument_string(self, quote=False):
        """Return the list of arguments as a string."""
        args = self._base_options + self.input_options + self.output_options
        if quote:
            return " ".join([ShellCommand.shellquote(a) for a in args])
        else:
            return " ".join(args)
    
    def argument_list(self):
        """Return a combined list of all arguments."""
        return self._base_options + self.input_options + self.output_options
    
    def command_string(self, quote=False):
        """Return the entire command as a string."""
        return "{exe} {arg}".format(exe=self.executable_string(quote),
                                    arg=self.argument_string(quote))
    
    def process_pattern(self, pat):
        """Respond to a pexpect pattern. Return True on EOF."""
        return (pat == 0)
    
    def run(self):
        """Execute the command in a subprocess."""
        self.process = pexpect.spawn(self.executable_string(),
                                     self.argument_list())
        # EOF is *always* the first pattern.
        patterns = self.process.compile_pattern_list(
            [pexpect.EOF] + self._expect_patterns)
        try:
            while True:
                i = self.process.expect_list(patterns, timeout=None)
                if self.process_pattern(i):
                    break
        except (KeyboardInterrupt):
            pass
        finally:
            if self.progress:
                self.progress.finish()
            self.process.close()
            return self.process.exitstatus
    
    def get_output(self):
        """Execute the command in a subprocess and return the output."""
        return pexpect.run(self.command_string(quote=True))


class ConvertCommand(ShellCommand):
    """An ImageMagick convert command."""
    _executable = distutils.spawn.find_executable("convert")
    _base_options = ["-density", "600",
                     "-size", "2048x1536",
                     "xc:dimgrey", "null:", # dark grey background
                     "("]
    
    def __init__(self, input_options=[], output_options=[]):
        super(ConvertCommand, self).__init__(input_options, output_options)
        self.append_input_options(
            ["-resize", "2048x1536",
             "-background", "white", 
             "-alpha", "remove",
             "-type", "truecolor", # force RGB (this and next line)
             "-define", "colorspace:auto-grayscale=off"])
        self.prepend_output_options([")",
                                     "-gravity", "center",
                                     "-layers", "composite",
                                     "-flatten"])
    

class FFprobeCommand(ShellCommand):
    """An ffprobe shell command."""
    _executable = distutils.spawn.find_executable("ffprobe")
    _base_options = ["-loglevel", "error",
                     "-show_entries", "format:stream",
                     "-print_format", "json"]
    
    def __init__(self, input_options=[], output_options=[]):
        super(FFprobeCommand, self).__init__(input_options, output_options)
        self.entries = None
        # The input file should be the last input option.
        assert(os.path.exists(self.input_options[-1]))
        self.last_modified = os.path.getmtime(self.input_options[-1])
    
    def get_entries(self, section="stream", find_list=[]):
        """Fetch specified attributes from the input file."""
        # Re-fetch if the file's changed since we last looked.
        modified = os.path.getmtime(self.input_options[-1])
        if (not self.entries) or (modified > self.last_modified):
            js = json.loads(self.get_output())
            print js
            self.entries = {"format": js["format"], "stream": js["streams"][0]}
        return [self.entries[section][f] for f in find_list]

    
class FFmpegCommand(ShellCommand):
    """A "simple" ffmpeg shell command."""
    _executable = distutils.spawn.find_executable("ffmpeg")
    _base_options = ["-y", "-nostdin"]
        

class FFmpegConcatCommand(FFmpegCommand):
    """An ffmpeg shell command with a complex concat filter."""
    _expect_patterns = [r"time=(\d\d):(\d\d):(\d\d\.\d\d)"]
    
    def __init__(self, input_options=[], output_options=[], quiet=False,
                 max_progress=100, has_audio=False, has_video=False):
        super(FFmpegConcatCommand, self).__init__(
            input_options, output_options)
        self.progress = ProgressBar(max_value=max_progress, quiet=quiet)
        self.has_video = has_video
        if (self.has_video):
            self.prepend_output_options(["-codec:v", "h264",
                                         "-pix_fmt", "yuv420p",
                                         "-map", "[vconc]"])
        self.has_audio = has_audio
        if (self.has_audio):
            self.prepend_output_options(["-codec:a", "pcm_s16le",
                                         "-ac", "1",
                                         "-map", "[anorm]"])
        self.filters = []
    
    def append_filter(self, filter):
        """Append a filter to the filters list."""
        if (filter):
            self.filters.append(filter)
        
    def append_normalisation_filter(self):
        """Append a normalisation audio filter to the complex filter."""
        if (self.has_audio):
            self.append_filter("[aconc] dynaudnorm=r=0.25:f=10:b=y [anorm]")
    
    def append_concat_filter(self, type, segments=[]):
        """Append a concat filter to the filters list"""
        if (len(segments) > 1):
            self.append_filter(
                "{inspecs} concat=n={n}:v={v}:a={a} [{t}conc]".format(
                    inspecs=" ".join([s.output_stream_specifier()
                                      for s in segments]),
                    n=len(segments), v=int(type == "v"),
                    a=int(type == "a"), t=type))
        elif (len(segments) == 1):
            self.append_filter(
                "{inspec} {a}null [{t}conc]".format(
                    inspec=segments[0].output_stream_specifier(),
                    a=type if type == "a" else "", t=type))
        
    def build_complex_filter(self):
        """Build the complete complex filter.
        
        Filters in the filtergraph are separated by ";".
        """
        return "{f}".format(f=";".join(self.filters))
    
    def argument_string(self, quote=False):
        """Return the list of arguments as a string."""
        args = (self._base_options + self.input_options +
                ["-filter_complex", self.build_complex_filter()] +
                self.output_options)
        if quote:
            return " ".join([ShellCommand.shellquote(a) for a in args])
        else:
            return " ".join(args)
    
    def argument_list(self):
        """Return a combined list of all arguments."""
        return (self._base_options + self.input_options +
                ["-filter_complex", self.build_complex_filter()] +
                self.output_options)
    
    def process_pattern(self, pat):
        """Respond to a pexpect pattern. Return True on EOF."""
        if (pat == 1):
            elapsed = datetime.timedelta(
                hours=int(self.process.match.group(1)),
                minutes=int(self.process.match.group(2)),
                seconds=float(self.process.match.group(3)))
            self.progress.update(elapsed.total_seconds())
        return (pat == 0)
    

if (__name__ == "__main__"):
    print ShellCommand()
    print ConvertCommand(input_options=["in.pdf[12]"], output_options=["out.png"])
    print FFprobeCommand(input_options=["-i", "in.mov"])
    print FFmpegCommand(input_options=["-i", "in.mov"],
                        output_options=["out.mov"])
    concat = FFmpegConcatCommand(input_options=["-i", "in.mov"],
                                 output_options=["out.mov"], has_audio=True)
    concat.append_normalisation_filter()
    print concat
