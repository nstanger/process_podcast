import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from segment import Segment
from shell_command import FFmpegConcatCommand
from test_shared import ShellCommandSharedTestCase


class FFmpegConcatCommandTestCase(ShellCommandSharedTestCase):
    """Test the FFmpegConcatCommand class."""

    # What about testing different permutations of audio and video?
    def setUp(self):
        """Set up for test."""
        # Make sure the input and output options are explicitly set,
        # otherwise they hang around from previous tests.
        self.command = FFmpegConcatCommand(
            input_options=["-i", "in.mov"], output_options=["out.mov"],
            has_video=True, has_audio=True, quiet=True)
        self.expected_executable = shutil.which("ffmpeg")
        self.expected_base_options = ["-y", "-nostdin",]
        self.expected_input_options = ["-i", "in.mov"]
        self.expected_filter_options = ["-filter_complex", ""]
        self.expected_output_options = [
            "-codec:a", self.command.audio_codec,
            "-ac", "1",
            "-map", "[anorm]",
            "-codec:v", self.command.video_codec,
            "-pix_fmt", "yuv420p",
            "-map", "[vconc]",
            "out.mov"
        ]

    def tearDown(self):
        """Clean up after test."""
        self.command = None
    
    def test_append_filter(self):
        """Test appending to the filter list."""
        # append empty filter => no change
        with self.subTest(msg="empty"):
            filters = []
            self.command.append_filter("")
            self.assertEqual(self.command.filters, filters)
        # append an actual filter
        with self.subTest(msg="normal"):
            filters = ["this_is_a_weird_filter"]
            self.command.append_filter("this_is_a_weird_filter")
            self.assertEqual(self.command.filters, filters)
    
    def test_append_normalisation_filter(self):
        """Test appending a normalisation filter."""
        filters = ["[aconc] dynaudnorm=r=0.25:f=10:b=y [anorm]"]
        self.command.append_normalisation_filter()
        self.assertEqual(self.command.filters, filters)
    
    def test_append_concat_filter_0(self):
        """Test appending a concat filter with no segments."""
        self.command.append_concat_filter(type="a", segments=[])
        with self.subTest(msg="audio"):
            self.assertEqual(self.command.filters, [])
        self.command.append_concat_filter(type="v", segments=[])
        with self.subTest(msg="video"):
            self.assertEqual(self.command.filters, [])
        self.command.append_concat_filter(type="f", segments=[])
        with self.subTest(msg="frame"):
            self.assertEqual(self.command.filters, [])
    
    def test_append_concat_filter_f(self):
        """Test appending a concat filter with a frame segment."""
        self.command.append_concat_filter(type="f", segments=[Segment()])
        self.assertEqual(
            self.command.filters, [],
            msg="frame segments should be ignored")
    
    # def test_append_concat_filter_1_a(self):
    #     """Test appending a concat filter with 1 audio segment."""
    #     self.command.append_concat_filter(
    #         type="a",
    #         segments=[Segment(file="a.mov", punch_in=10,
    #                   punch_out=20, input_stream=1)])
    #     with self.subTest(msg="audio"):
    #         self.assertEqual(self.command.filters, [])
    
    # def test_append_concat_filter_1_v(self):
    #     """Test appending a concat filter with 1 video segment."""
    #     concat = 
    #     self.command.append_concat_filter(type="v",
    #         segments=[Segment(file="v.mov", punch_in=10,
    #             punch_out=20, input_stream=1)])
    #     with self.subTest(msg="audio"):
    #         self.assertEqual()
    
    # def test_append_concat_filter_2(self):
    #     """Test appending a concat filter with >1 segment."""
    
    # def test_build_complex_filter(self):
    #     """Test building the complex filter."""


# Remove ShellCommandSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(ShellCommandSharedTestCase)
