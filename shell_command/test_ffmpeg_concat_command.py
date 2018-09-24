from datetime import timedelta
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from segment import Segment, AudioSegment, VideoSegment
from shell_command import FFmpegConcatCommand
from shell_command.shared_tests import ShellCommandSharedTestCase


class FFmpegConcatCommandTestCase(ShellCommandSharedTestCase):
    """Test the FFmpegConcatCommand class."""

    NORMALISATION_FILTER = "[aconc] dynaudnorm=r=0.25:f=10:b=y [anorm]"

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
        filters = [self.NORMALISATION_FILTER]
        self.command.append_normalisation_filter()
        self.assertEqual(self.command.filters, filters)
    
    def test_append_concat_filter(self):
        """Test appending various concat filters."""
        test_data = (
            ("a", "audio"),
            ("v", "video"),
            ("f", "frame (should be ignored)"),
        )
        expected = []
        for frame_type, description in test_data:
            for num_segments in range(0, 3):
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
                    # Frame segments should be ignored by
                    # append_concat_filter() regardless.
                    segments = []
                else:
                    raise TypeError
                self.command.append_concat_filter(
                    frame_type=frame_type, segments=segments)
                if frame_type not in ["a", "v"]:
                    # Ignore frame segments.
                    pass
                elif num_segments > 1:
                    expected.append(
                        "{inspecs} concat=n={n}:v={v}:a={a} [{t}conc]".format(
                            inspecs=" ".join([s.output_stream_specifier()
                                              for s in segments]),
                            n=num_segments, v=int(frame_type == "v"),
                            a=int(frame_type == "a"), t=frame_type)
                    )
                elif num_segments == 1:
                    expected.append(
                        "{inspec} {a}null [{t}conc]".format(
                            inspec=segments[0].output_stream_specifier(),
                            a=frame_type if frame_type == "a" else "",
                            t=frame_type)
                    )
                with self.subTest(
                        msg="{d}: {n}".format(d=description, n=num_segments)):
                    self.assertEqual(self.command.filters, expected)

    def test_build_complex_filter(self):
        self.command.append_normalisation_filter()
        self.assertEqual(
            self.command.build_complex_filter(), self.NORMALISATION_FILTER)
        test_data = (
            ("", self.NORMALISATION_FILTER, "append empty filter"),
            ("normal_filter",
             "{n};normal_filter".format(n=self.NORMALISATION_FILTER),
             "append normal filter"),
        )
        for appended, expected, description in test_data:
            with self.subTest(msg=description):
                self.command.append_filter(appended)
                self.assertEqual(self.command.build_complex_filter(), expected)

# process_pattern() updates the internal ProgressBar object.


# Remove ShellCommandSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(ShellCommandSharedTestCase)
