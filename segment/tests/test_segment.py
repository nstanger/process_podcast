from datetime import timedelta
from pathlib import Path
import unittest

from segment import Segment
from segment.tests import SegmentSharedTestCase


class SegmentTestCase(SegmentSharedTestCase):
    """Test the Segment class."""

    def test_input_files(self):
        """Test list of input files (static method)."""
        self.assertEqual(Segment.input_files(), self.EXPECTED_FILE_LIST)

    def test_rename_input_file(self):
        """Test input file renaming (static method)."""
        Segment._rename_input_file(self.EXPECTED_INPUT_FILE, "file.new")
        self.assertEqual(Segment.input_files(), {"file.new": None})
    

# Remove SegmentSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(SegmentSharedTestCase)
