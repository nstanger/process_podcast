import shutil
from pathlib import Path
import tempfile
import unittest

from shell_command import FFmpegCommand
from test_shared import ShellCommandSharedTestCase


class FFmpegCommandTestCase(ShellCommandSharedTestCase):
    """Test the FFmpegCommand class.
    """

    def setUp(self):
        """Initialisation. Make sure the input and output options are
        explicitly set otherwise they hang around from previous tests.
        A fresh temporary file is created for each test.
        """
        self.command = FFmpegCommand(
            input_options=["-i", "in.mov"], output_options=["out.mov"])
        self.expected_executable = shutil.which("ffmpeg")
        self.expected_base_options = ["-y", "-nostdin",]
        self.expected_input_options = ["-i", "in.mov"]
        self.expected_output_options = ["out.mov"]

    def tearDown(self):
        """Cleanup.
        """
        self.command = None
    

# Remove ShellCommandSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(ShellCommandSharedTestCase)
