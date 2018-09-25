import unittest

from segment import VideoSegment
from segment.tests import SegmentSharedTestCase


class VideoSegmentTestCase(SegmentSharedTestCase):
    """Test the VideoSegment class."""

    EXPECTED_TYPE = "video"
    EXPECTED_TRIM = "trim"
    EXPECTED_SETPTS = "setpts"

    def setUp(self):
        """Set up for test."""
        super().setUp()
        self.segment = VideoSegment(
            file=self.EXPECTED_INPUT_FILE,
            punch_in=self.EXPECTED_PUNCH_IN,
            punch_out=self.EXPECTED_PUNCH_OUT,
            input_stream=self.EXPECTED_INPUT_STREAM)
        self.expected_output_options = [
            "-map", "{n}:v".format(n=self.segment.input_stream)
        ]
    
    def test_init(self):
        """Test segment initialises correctly."""
        super().test_init()
        self.assertEqual(self.segment._temp_frame_file, "")
    
    # Tricky to test get_last_frame_number() and generate_frame()
    # because they use pexpect.
    

# Remove SegmentSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(SegmentSharedTestCase)
