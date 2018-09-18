import shutil
import unittest

from shell_command import (
    ShellCommand, ConvertCommand
)


class TestConvertCommand(unittest.TestCase):
    """Test the ConvertCommand class.
    """

    # Local ConvertCommand.
    command = None

    # Path to convert executable.
    expected_executable = shutil.which("convert")

    # Expected base options.
    expected_base_options = [
        "-size", "2048x1536",
        "-density", "600",
        "xc:dimgrey", "null:",
        "("
    ]

    # Expected input options.
    expected_input_options = [
        "foo",
        "-resize", "2048x1536",
        "-background", "white", 
        "-alpha", "remove",
        "-type", "truecolor",
        "-define", "colorspace:auto-grayscale=off",
    ]

    # Expected output options.
    expected_output_options = [
        ")",
        "-gravity", "center",
        "-layers", "composite",
        "-flatten",
        "bar",
    ]

    def setUp(self):
        """Initialisation. Make sure the input and output options are
        explicitly set otherwise they hang around from previous tests.
        """
        self.command = ConvertCommand(
            input_options=["foo"], output_options=["bar"])

    def tearDown(self):
        """Cleanup.
        """
        self.command = None
    
    def test_base_options(self):
        """Test that base options match expected.
        """
        self.assertEqual(
            self.command._base_options, self.expected_base_options)
    
    def test_input_options(self):
        """Test that input options match expected.
        """
        self.assertEqual(
            self.command.input_options, self.expected_input_options)
    
    def test_output_options(self):
        """Test that output options match expected.
        """
        self.assertEqual(
            self.command.output_options, self.expected_output_options)
    
    def test_executable_string(self):
        """Test that executable path matches expected.
        """
        self.assertEqual(self.command.executable_string(quote=False),
            self.expected_executable)
        # Note: don't explicitly specify quoted value, because
        # the executable path will vary across different systems.
        self.assertEqual(self.command.executable_string(quote=True),
            ShellCommand.shellquote(self.expected_executable))

    def test_argument_string(self):
        """Test that the argument string matches expected.
        """
        args = (self.expected_base_options + self.expected_input_options +
            self.expected_output_options)
        self.assertEqual(self.command.argument_string(quote=False),
            " ".join(args))
        self.assertEqual(self.command.argument_string(quote=True),
            " ".join([ShellCommand.shellquote(a) for a in args]))

    def test_argument_list(self):
        """Test that the argument list matches expected.
        """
        self.assertEqual(self.command.argument_list(),
            self.expected_base_options + self.expected_input_options +
            self.expected_output_options)

    def test_command_string(self):
        """Test that the command string matches expected.
        """
        args = (self.expected_base_options + self.expected_input_options +
            self.expected_output_options)
        expected_cmd_unquoted = (
            "{exe} {arg}".format(exe=self.expected_executable,
                arg=" ".join(args))
        )
        expected_cmd_quoted = (
            '{exe} {arg}'.format(
                exe=ShellCommand.shellquote(self.expected_executable),
                arg=" ".join([ShellCommand.shellquote(a) for a in args]))
        )
        self.assertEqual(self.command.command_string(quote=False),
            expected_cmd_unquoted)
        self.assertEqual(self.command.command_string(quote=True),
            expected_cmd_quoted)
