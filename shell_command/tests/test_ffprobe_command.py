import shutil
from pathlib import Path
import tempfile
import unittest

from shell_command import FFprobeCommand
from shell_command.tests import ShellCommandSharedTestCase


class FFprobeCommandTestCase(ShellCommandSharedTestCase):
    """Test the FFprobeCommand class."""

    def setUp(self):
        """Set up for test."""
        # Make sure the input and output options are explicitly set,
        # otherwise they hang around from previous tests. A fresh
        # temporary file is created for each test.
        self.tmpfile = tempfile.NamedTemporaryFile()
        self.command = FFprobeCommand(
            input_options=["-i", self.tmpfile.name], output_options=[])
        self.expected_executable = shutil.which("ffprobe")
        self.expected_base_options = [
            "-loglevel", "error",
            "-show_entries", "format:stream",
            "-print_format", "json",
        ]
        self.expected_input_options = ["-i", self.tmpfile.name]
        self.expected_filter_options = []
        self.expected_output_options = []

    def tearDown(self):
        """Clean up after test."""
        self.tmpfile.close()
        self.command = None
    
    def test_last_modified(self):
        """Test that last modified time of temp file matches."""
        self.assertEqual(
            self.command.last_modified,
            Path(self.tmpfile.name).stat().st_mtime)

    # get_entries()?
    

# Remove ShellCommandSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(ShellCommandSharedTestCase)
