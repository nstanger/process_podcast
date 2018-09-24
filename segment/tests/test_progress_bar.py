from contextlib import contextmanager
from io import StringIO
import sys
import unittest

from progress_bar import ProgressBar


@contextmanager
def captured_output():
    """Capture stdout and stderr so we can assert against them."""
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class ProgressBarTestCase(unittest.TestCase):
    """Test the ProgressBar class."""

    DEFAULT_VALUE = 0
    DEFAULT_MAX_VALUE = 100
    DEFAULT_PRINT_WIDTH = 50
    DEFAULT_NEWLINE = "\r"

    def setUp(self):
        """Set up for test."""
        self.bar = ProgressBar(quiet=True)

    def tearDown(self):
        """Clean up after test."""
        self.bar = None
    
    def test_defaults(self):
        """Test default values are correct."""
        test_data = (
            (self.bar.value, self.DEFAULT_VALUE,
             "default value = {v}".format(v=self.DEFAULT_VALUE)),
            (self.bar.initial_value, self.DEFAULT_VALUE,
             "default initial value = {v}".format(v=self.DEFAULT_VALUE)),
            (self.bar.max_value, self.DEFAULT_MAX_VALUE,
             "default max value = {v}".format(v=self.DEFAULT_MAX_VALUE)),
            (self.bar.print_width, self.DEFAULT_PRINT_WIDTH,
             "default print width = {v}".format(v=self.DEFAULT_PRINT_WIDTH)),
            (self.bar.newline, self.DEFAULT_NEWLINE,
             "default newline = {v}".format(v=self.DEFAULT_NEWLINE)),
        )
        for actual, expected, description in test_data:
            with self.subTest(msg=description):
                self.assertEqual(actual, expected)
    
    def test_set_and_reset(self):
        """Test setting and resetting the current value."""
        self.bar.set(value=50)
        self.assertEqual(self.bar.value, 50)
        self.bar.reset()
        self.assertEqual(self.bar.value, 0)
    
    def test_update_ad_draw(self):
        """Test updating and drawing the progress bar."""
        self.bar.reset()
        self.bar.quiet = False
        for i in range(self.bar.initial_value, self.bar.max_value + 1):
            percent = int(i * 100 / self.bar.max_value)
            dots = int(i * self.bar.print_width / self.bar.max_value)
            expected_bar = "{nl}[{c}{nc}] {p}% ".format(
                c="".join(["+"] * dots),
                nc="".join(["."] * (self.bar.print_width - dots)),
                p=percent, nl=self.bar.newline)
            with captured_output() as (out, _):
                self.bar.update(i)
            with self.subTest(msg="value = {v}".format(v=i)):
                self.assertEqual(self.bar.value, i)
            with self.subTest(msg="output = {v}".format(v=expected_bar)):
                self.assertEqual(out.getvalue(), expected_bar)
