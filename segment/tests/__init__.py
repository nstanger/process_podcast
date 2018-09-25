from datetime import timedelta
from pathlib import Path
import unittest

from segment import Segment


class SegmentSharedTestCase(unittest.TestCase):
    """Shared tests for Segment and its subclasses."""

    EXPECTED_INPUT_FILE = "file.in"
    EXPECTED_PUNCH_IN = timedelta(seconds=10)
    EXPECTED_PUNCH_OUT = timedelta(minutes=5, seconds=10)
    EXPECTED_DURATION = (EXPECTED_PUNCH_OUT - EXPECTED_PUNCH_IN).total_seconds()
    EXPECTED_INPUT_STREAM = 1
    EXPECTED_FILE_LIST = {"{f}".format(f=EXPECTED_INPUT_FILE): None}
    EXPECTED_TEMP_FILE = ""
    EXPECTED_TEMP_SUFFIX = ".mov"
    EXPECTED_TEMP_LIST = []
    EXPECTED_TYPE = ""
    EXPECTED_TRIM = ""
    EXPECTED_SETPTS = ""

    def setUp(self):
        """Set up for test."""
        # Explicitly empty the list of segment input files,
        # otherwise they hang around from previous tests.
        Segment._input_files = {}
        self.segment = Segment(
            file=self.EXPECTED_INPUT_FILE,
            punch_in=self.EXPECTED_PUNCH_IN,
            punch_out=self.EXPECTED_PUNCH_OUT,
            input_stream=self.EXPECTED_INPUT_STREAM)
        self.expected_input_options = [
            "-ss", str(self.EXPECTED_PUNCH_IN.total_seconds()),
            "-t", str(self.EXPECTED_DURATION),
            "-i", self.EXPECTED_INPUT_FILE
        ]
        self.expected_output_options = []

    def tearDown(self):
        """Clean up after test."""
        self.segment = None

    def test_init(self):
        """Test segment initialises correctly."""
        test_data = (
            (self.segment.input_file, self.EXPECTED_INPUT_FILE,
             "input file = {v}".format(v=self.EXPECTED_INPUT_FILE)),
            (self.segment.punch_in, self.EXPECTED_PUNCH_IN,
             "punch in = {v}".format(v=self.EXPECTED_PUNCH_IN)),
            (self.segment.punch_out, self.EXPECTED_PUNCH_OUT,
             "punch out = {v}".format(v=self.EXPECTED_PUNCH_OUT)),
            (self.segment.input_stream, self.EXPECTED_INPUT_STREAM,
             "input stream = {v}".format(v=self.EXPECTED_INPUT_STREAM)),
            (self.segment._temp_file, self.EXPECTED_TEMP_FILE,
             "temp file = {v}".format(v=self.EXPECTED_TEMP_FILE)),
            (self.segment._temp_suffix, self.EXPECTED_TEMP_SUFFIX,
             "temp suffix = {v}".format(v=self.EXPECTED_TEMP_SUFFIX)),
            (self.segment._temp_files_list, self.EXPECTED_TEMP_LIST,
             "temp files list = {v}".format(v=self.EXPECTED_TEMP_LIST)),
            (self.segment._TYPE, self.EXPECTED_TYPE,
             "type = {v}".format(v=self.EXPECTED_TYPE)),
            (self.segment._TRIM, self.EXPECTED_TRIM,
             "trim = {v}".format(v=self.EXPECTED_TRIM)),
            (self.segment._SETPTS, self.EXPECTED_SETPTS,
             "setpts = {v}".format(v=self.EXPECTED_SETPTS)),
        )
        for actual, expected, description in test_data:
            with self.subTest(msg=description):
                self.assertEqual(actual, expected)
    
    def test_input_options(self):
        """Test input options match expected."""
        # These are tested separately because they are initialised
        # differently by subclasses.
        self.assertEqual(
            self.segment._input_options, self.expected_input_options)

    def test_output_options(self):
        """Test output options match expected."""
        # These are tested separately because they are initialised
        # differently by subclasses.
        self.assertEqual(
            self.segment._output_options, self.expected_output_options)

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
    
    # Testing generate_temp_file() is messy because of pexpect.

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

    def test_input_stream_specifier(self):
        """Test that input stream specifier is correctly generated."""
        expected_specifier = "[{n}:{t}]".format(
            n=tuple(Segment._input_files).index(self.segment.input_file),
            t=self.segment._TYPE[0] if self.segment._TYPE else "")
        self.assertEqual(
            self.segment.input_stream_specifier(), expected_specifier)

    def test_output_stream_specifier(self):
        """Test that output stream specifier is correctly generated."""
        expected_specifier = "[{t}{n}]".format(
            t=self.segment._TYPE[0] if self.segment._TYPE else "",
            n=self.segment.segment_number)
        self.assertEqual(
            self.segment.output_stream_specifier(), expected_specifier)
    
    def test_trim_filter(self):
        """Test that the trim filter is correctly generated."""
        expected_filter = (
            "{inspec} {trim}=start={pi}:duration={d},{setpts}=PTS-STARTPTS "
            "{outspec}".format(
                inspec=self.segment.input_stream_specifier(),
                trim=self.segment._TRIM, setpts=self.segment._SETPTS,
                pi=self.EXPECTED_PUNCH_IN.total_seconds(),
                d=self.EXPECTED_DURATION,
                outspec=self.segment.output_stream_specifier()))
        self.assertEqual(self.segment.trim_filter(), expected_filter)
