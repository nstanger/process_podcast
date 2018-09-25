import unittest

from segment import AudioSegment
from segment.tests import SegmentSharedTestCase


class AudioSegmentTestCase(SegmentSharedTestCase):
    """Test the AudioSegment class."""

    EXPECTED_TEMP_SUFFIX = ".wav"
    EXPECTED_TYPE = "audio"
    EXPECTED_TRIM = "atrim"
    EXPECTED_SETPTS = "asetpts"

    def setUp(self):
        """Set up for test."""
        super().setUp()
        self.segment = AudioSegment(
            file=self.EXPECTED_INPUT_FILE,
            punch_in=self.EXPECTED_PUNCH_IN,
            punch_out=self.EXPECTED_PUNCH_OUT,
            input_stream=self.EXPECTED_INPUT_STREAM)
        self.expected_output_options = [
            "-ac", "1",
            "-map", "{n}:a".format(n=self.segment.input_stream)
        ]
    

# Remove SegmentSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(SegmentSharedTestCase)
