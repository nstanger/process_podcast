import shutil
import unittest

from shell_command import ConvertCommand
from shell_command.shared_tests import ShellCommandSharedTestCase


class ConvertCommandTestCase(ShellCommandSharedTestCase):
    """Test the ConvertCommand class."""

    def setUp(self):
        """Set up for test."""
        # Make sure the input and output options are explicitly set,
        # otherwise they hang around from previous tests.
        self.command = ConvertCommand(
            input_options=["in.pdf[12]"], output_options=["out.png"])
        self.expected_executable = shutil.which("convert")
        self.expected_base_options = [
            "-size", "2048x1536",
            "-density", "600",
            "xc:dimgrey", "null:",
            "("
        ]
        self.expected_input_options = [
            "in.pdf[12]",
            "-resize", "2048x1536",
            "-background", "white", 
            "-alpha", "remove",
            "-type", "truecolor",
            "-define", "colorspace:auto-grayscale=off",
        ]
        self.expected_filter_options = []
        self.expected_output_options = [
            ")",
            "-gravity", "center",
            "-layers", "composite",
            "-flatten",
            "out.png",
        ]

    def tearDown(self):
        """Clean up after test."""
        self.command = None
    

# Remove ShellCommandSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(ShellCommandSharedTestCase)
