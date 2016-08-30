#!/usr/bin/env python

import distutils.spawn
import re
import subprocess


class ShellCommand(object):
    """A shell command.
    
    _executable contains the full path to the relevant executable.
    
    _base_options is a list of standard general options for this
    command.
    """
    _executable = ""
    _base_options = []
    
    def __init__(self, input_options=[], output_options=[]):
        self.input_options = input_options
        self.output_options = output_options
    
    def __repr__(self):
        return "<{cls}: {cmd}>".format(
            cls=self.__class__.__name__,
            cmd=" ".join(self.command_items(True)))

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
    
    def run(self):
        """Execute the command in a subprocess."""
        return subprocess.call(self.command_items())
    
    def get_output(self):
        """Execute the command in a subprocess and return the output."""
        return subprocess.check_output(self.command_items())


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
    
    def command_items(self, debug=False):
        """Return the list of items representing the command."""
        base_opts = self._base_options
        input_opts = self.input_options
        output_opts = self.output_options
        if (debug):
            # Wrap frame specifiers in 'single quotes' and prefix
            # parentheses with backslashes, so that we can copy and
            # paste the command string directly into the shell for
            # testing.
            base_opts = [re.sub(r"\(", r"\\(", s)
                         for s in self._base_options]
            input_opts = [re.sub(r"\[(\d+)\]", r"'[\1]'", s)
                          for s in self.input_options]
            output_opts = [re.sub(r"\)", r"\\)", s)
                           for s in self.output_options]
        return ([self._executable] + base_opts + input_opts + output_opts)
    

class FFprobeCommand(ShellCommand):
    """An ffprobe shell command."""
    _executable = distutils.spawn.find_executable("ffprobe")
    _base_options = ["-loglevel", "error"]

    
class FFmpegCommand(ShellCommand):
    """A "simple" ffmpeg shell command."""
    _executable = distutils.spawn.find_executable("ffmpeg")
    _base_options = ["-y", "-loglevel", "error", "-nostdin"]
        

class FFmpegConcatCommand(FFmpegCommand):
    """An ffmpeg shell command with a complex concat filter."""
    def __init__(self, input_options=[], output_options=[]):
        super(FFmpegConcatCommand, self).__init__(
            input_options, output_options)
        self.prepend_output_options(["-codec:a", "pcm_s16le",
                                     "-ac", "1",
                                     "-codec:v", "h264",
                                     "-pix_fmt", "yuv420p",
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
    

if (__name__ == "__main__"):
    print ShellCommand()
    print ConvertCommand(input_options=["in.pdf[12]"], output_options=["out.png"])
    print FFprobeCommand(input_options=["-i", "in.mov"])
    print FFmpegCommand(input_options=["-i", "in.mov"],
                        output_options=["out.mov"])
    concat = FFmpegConcatCommand(input_options=["-i", "in.mov"],
                                 output_options=["out.mov"])
    concat.append_normalisation_filter()
    print concat
