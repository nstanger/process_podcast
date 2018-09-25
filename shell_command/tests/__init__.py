import unittest

from shell_command import ShellCommand


class ShellCommandSharedTestCase(unittest.TestCase):
    """Shared tests for ShellCommand and its subclasses."""

    def setUp(self):
        """Set up for test."""
        # Make sure the input and output options are explicitly set to
        # [] otherwise they hang around from previous tests.
        self.command = ShellCommand(input_options=[], output_options=[])
        self.expected_executable = ""
        self.expected_base_options = []
        self.expected_input_options = []
        self.expected_filter_options = []
        self.expected_output_options = []

    def tearDown(self):
        """Clean up after test."""
        self.command = None

    def test_base_options(self):
        """Test that base options match expected."""
        self.assertEqual(
            self.command._base_options, self.expected_base_options)
    
    def test_input_options(self):
        """Test that input options match expected."""
        self.assertEqual(
            self.command.input_options, self.expected_input_options)
    
    def test_output_options(self):
        """Test that output options match expected."""
        self.assertEqual(
            self.command.output_options, self.expected_output_options)
    
    def test_executable_string(self):
        """Test that executable path matches expected."""
        with self.subTest(msg="unquoted paths match"):
            self.assertEqual(
                self.command.executable_string(quote=False),
                self.expected_executable)
        with self.subTest(msg="unquoted paths match"):
            # Note: don't explicitly specify quoted value, because
            # the executable path will vary across different systems.
            self.assertEqual(
                self.command.executable_string(quote=True),
                ShellCommand.shellquote(self.expected_executable))

    def test_argument_string(self):
        """Test that argument string matches expected."""
        args = (self.expected_base_options + self.expected_input_options +
            self.expected_filter_options + self.expected_output_options)
        with self.subTest(msg="unquoted agruments match"):
            self.assertEqual(
                self.command.argument_string(quote=False), " ".join(args))
        with self.subTest(msg="quoted agruments match"):
            self.assertEqual(
                self.command.argument_string(quote=True),
                " ".join([ShellCommand.shellquote(a) for a in args]))

    def test_argument_list(self):
        """Test that argument list matches expected."""
        self.assertEqual(self.command.argument_list(),
            self.expected_base_options + self.expected_input_options +
            self.expected_filter_options + self.expected_output_options)

    def test_command_string(self):
        """Test that command string matches expected."""
        args = (self.expected_base_options + self.expected_input_options +
            self.expected_filter_options + self.expected_output_options)
        expected_cmd_unquoted = (
            "{exe} {arg}".format(exe=self.expected_executable,
                arg=" ".join(args))
        )
        expected_cmd_quoted = (
            '{exe} {arg}'.format(
                exe=ShellCommand.shellquote(self.expected_executable),
                arg=" ".join([ShellCommand.shellquote(a) for a in args]))
        )
        with self.subTest(msg="unquoted command string matches"):
            self.assertEqual(
                self.command.command_string(quote=False),
                expected_cmd_unquoted)
        with self.subTest(msg="quoted command string matches"):
            self.assertEqual(
                self.command.command_string(quote=True), expected_cmd_quoted)
