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

    def test_segment_number_increment(self):
        """Test that the segment number increments correctly."""
        segment_1, segment_2 = Segment(), Segment()
        self.assertEqual(
            segment_1.segment_number + 1, segment_2.segment_number)
    
    def test_get_duration(self):
        """Test duration calculation."""
        self.assertEqual(self.segment.get_duration(), self.EXPECTED_DURATION)
    
    def test_generate_temp_filename(self):
        """Test generating temporary filename."""
        test_data = (
            (None, "default suffix"),
            (".bar", "specified suffix (.bar)"),
        )
        for suffix, description in test_data:
            expected_path = Path("temp_{t}_{o}_{n:03d}".format(
                t=self.segment._TYPE, o=Path("file.out").stem,
                n=self.segment.segment_number)).with_suffix(
                    suffix if suffix is not None
                           else self.segment._temp_suffix)
            with self.subTest(msg=description):
                self.assertEqual(self.segment.generate_temp_filename(
                                     "file.out", suffix=suffix),
                                 expected_path)
    
    def test_temp_file(self):
        """Test that temporary filename is correct."""
        self.assertEqual(
            self.segment.temp_file(), "", msg="temp file initially empty")
        self.segment._temp_file = self.segment.generate_temp_filename(
            "file.out", ".bar")
        expected_path = Path("temp_{t}_{o}_{n:03d}".format(
            t=self.segment._TYPE, o=Path("file.out").stem,
            n=self.segment.segment_number)).with_suffix(".bar")
        self.assertEqual(
            self.segment.temp_file(), expected_path,
            msg="specified temp file is correct")
    
    # Testing delete_temp_files() requires actual files to be created.
    

# Remove SegmentSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(SegmentSharedTestCase)
