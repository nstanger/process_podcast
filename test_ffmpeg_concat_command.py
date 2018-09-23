from datetime import timedelta
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from segment import Segment, AudioSegment, FrameSegment, VideoSegment
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
        test_data = (
            ("", [], "append empty filter"),
            ("normal_filter", ["normal_filter"], "append normal filter"),
        )
        for appended, expected, description in test_data:
            with self.subTest(msg=description):
                self.command.append_filter(appended)
                self.assertEqual(self.command.filters, expected)
    
    def test_append_normalisation_filter(self):
        """Test appending a normalisation filter."""
        filters = ["[aconc] dynaudnorm=r=0.25:f=10:b=y [anorm]"]
        self.command.append_normalisation_filter()
        self.assertEqual(self.command.filters, filters)
    
    def test_append_concat_filter(self):
        """Test appending various concat filters."""
        test_data = (
            ("a", "audio"),
            # ("v", "video"),
            # ("f", "frame"),
        )
        for frame_type, description in test_data:
            for num_segments in range(0, 3):
                print("[{t}{n}]".format(t=frame_type, n=num_segments))
                segments = None
                if frame_type == "a":
                    segments = num_segments * [AudioSegment(
                        file="file.in", punch_in=timedelta(),
                        punch_out=timedelta(seconds=20), input_stream=0)]
                elif frame_type == "v":
                    segments = num_segments * [VideoSegment(
                        file="file.in", punch_in=timedelta(),
                        punch_out=timedelta(seconds=20), input_stream=0)]
                elif frame_type == "f":
                    segments = num_segments * [FrameSegment(
                        file="file.in", punch_in=timedelta(),
                        punch_out=timedelta(seconds=20), input_stream=0,
                        frame_number=1)]
                else:
                    raise TypeError
                self.command.append_concat_filter(
                    frame_type=frame_type, segments=segments)
                if num_segments > 1:
                    expected = [
                        "{inspecs} concat=n={n}:v={v}:a={a} [{t}conc]".format(
                            inspecs=" ".join([s.output_stream_specifier()
                                            for s in segments]),
                            n=num_segments, v=int(type == "v"),
                            a=int(type == "a"), t=frame_type)
                    ]
                elif num_segments == 1:
                    expected = [
                        "{inspec} {a}null [{t}conc]".format(
                            inspec=segments[0].output_stream_specifier(),
                            a=frame_type if frame_type == "a" else "",
                            t=frame_type)
                    ]
                else:
                    expected = []
                print("  expected: {}".format(expected))
                print("  actual:   {}".format(self.command.filters))
                with self.subTest(
                        msg="{d}: {n}".format(d=description, n=num_segments)):
                    self.assertEqual(self.command.filters, expected)

    # def test_append_concat_filter_0(self):
    #     """Test appending a concat filter with no segments."""
    #     self.command.append_concat_filter(type="a", segments=[])
    #     with self.subTest(msg="audio"):
    #         self.assertEqual(self.command.filters, [])
    #     self.command.append_concat_filter(type="v", segments=[])
    #     with self.subTest(msg="video"):
    #         self.assertEqual(self.command.filters, [])
    #     self.command.append_concat_filter(type="f", segments=[])
    #     with self.subTest(msg="frame"):
    #         self.assertEqual(self.command.filters, [])
    
    # def test_append_concat_filter_f(self):
    #     """Test appending a concat filter with a frame segment."""
    #     self.command.append_concat_filter(type="f", segments=[Segment()])
    #     self.assertEqual(
    #         self.command.filters, [],
    #         msg="frame segments should be ignored")
    
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
