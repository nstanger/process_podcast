import unittest

from segment import Segment, FrameSegment
from segment.tests import SegmentSharedTestCase


class FrameSegmentTestCase(SegmentSharedTestCase):
    """Test the FrameSegment class."""

    EXPECTED_TYPE = "frame"
    EXPECTED_TRIM = "trim"
    EXPECTED_SETPTS = "setpts"
    EXPECTED_FRAME_NUMBER = 42

    def setUp(self):
        """Set up for test."""
        super().setUp()
        self.segment = FrameSegment(
            file=self.EXPECTED_INPUT_FILE,
            punch_in=self.EXPECTED_PUNCH_IN,
            punch_out=self.EXPECTED_PUNCH_OUT,
            input_stream=self.EXPECTED_INPUT_STREAM,
            frame_number=self.EXPECTED_FRAME_NUMBER)
        self.expected_input_options = [
            "-loop", "1",
            "-t", str(self.EXPECTED_DURATION),
            "-i", self.EXPECTED_INPUT_FILE,
        ]
        self.expected_output_options = [
            "-map", "{n}:v".format(n=self.segment.input_stream)
        ]
    
    def test_init(self):
        """Test segment initialises correctly."""
        super().test_init()
        self.assertEqual(
            self.segment.frame_number, self.EXPECTED_FRAME_NUMBER,
            msg="frame number = {v}".format(v=self.EXPECTED_FRAME_NUMBER))
        self.assertEqual(
            Segment._input_files[self.EXPECTED_INPUT_FILE],
            self.expected_input_options[:4],
            msg="input file {f}: {v}".format(
                f=self.EXPECTED_INPUT_FILE,
                v=self.expected_input_options[:4]))
    
    # Tricky to test generate_temp_file() because it uses pexpect.
    # use_frame() relies on the output from generate_temp_frame()
    # or generate_frame().

    # def test_use_frame(self):
    #     self.segment.use_frame()
    #     pass
    
    def test_input_stream_specifier(self):
        """Test that input stream specifier is correctly generated."""
        expected_specifier = "[{n}:v]".format(
            n=tuple(Segment._input_files).index(self.segment.input_file))
        self.assertEqual(
            self.segment.input_stream_specifier(), expected_specifier)

    def test_output_stream_specifier(self):
        """Test that output stream specifier is correctly generated."""
        expected_specifier = "[{n}:v]".format(
            n=tuple(Segment._input_files).index(self.segment.input_file))
        self.assertEqual(
            self.segment.output_stream_specifier(), expected_specifier)
    
    def test_trim_filter(self):
        """Test that the trim filter is correctly generated."""
        self.assertEqual(self.segment.trim_filter(), "")
    

# Remove SegmentSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(SegmentSharedTestCase)
