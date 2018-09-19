import unittest

from shell_command import (
    ShellCommand, ConvertCommand, FFmpegConcatCommand, FFprobeCommand
)


class ShellCommandTestCase(unittest.TestCase):
    """Test the ShellCommand class.
    """

    def setUp(self):
        """Initialisation. Make sure the input and output options are
        explicitly set to [] otherwise they hang around from previous
        tests.
        """
        self.command = ShellCommand(input_options=[], output_options=[])

    def tearDown(self):
        """Cleanup.
        """
        self.command = None

    def test_shellquote(self):
        """Test static method ShellCommand.shellquote().
        """
        # None => None
        self.assertIsNone(ShellCommand.shellquote(None))
        # (empty string) => (empty string)
        self.assertEqual(ShellCommand.shellquote(""), "")
        # (blank) => " " (one or more)
        self.assertEqual(ShellCommand.shellquote(" "), '" "')
        self.assertEqual(ShellCommand.shellquote("     "), '"     "')
        # foobar => foobar
        self.assertEqual(ShellCommand.shellquote("foobar"), "foobar")
        # foo bar => "foo bar"
        self.assertEqual(ShellCommand.shellquote("foo bar"), '"foo bar"')
        # "foobar" => '"foobar"'
        self.assertEqual(ShellCommand.shellquote('"foobar"'), '\'"foobar"\'')
        # 'foobar' => 'foobar'
        self.assertEqual(ShellCommand.shellquote("'foobar'"), "'foobar'")
        # foo 'bar' => "foo 'bar'"
        self.assertEqual(
            ShellCommand.shellquote("foo 'bar'"), '"foo \'bar\'"')
        # foo"bar => 'foo"bar'
        self.assertEqual(ShellCommand.shellquote('foo"bar'), '\'foo"bar\'')
        # foo.bar => "foo.bar"
        self.assertEqual(ShellCommand.shellquote("foo.bar"), '"foo.bar"')
        # foo(bar) => "foo(bar)"
        self.assertEqual(ShellCommand.shellquote("foo(bar)"), '"foo(bar)"')
        # [foobar] => "[foobar]"
        self.assertEqual(ShellCommand.shellquote("[foobar]"), '"[foobar]"')
        # foo[bar => "foo[bar"
        self.assertEqual(ShellCommand.shellquote("foo[bar"), '"foo[bar"')
        # /foo/bar => /foo/bar
        self.assertEqual(ShellCommand.shellquote("/foo/bar"), "/foo/bar")
        # -f => -f
        self.assertEqual(ShellCommand.shellquote("-f"), "-f")
        # --foobar => --foobar
        self.assertEqual(ShellCommand.shellquote("--foobar"), "--foobar")
        # ( => \(
        self.assertEqual(ShellCommand.shellquote("("), r"\(")
        # ) => \)
        self.assertEqual(ShellCommand.shellquote(")"), r"\)")
        # ' => "'"
        self.assertEqual(ShellCommand.shellquote("'"), '"\'"')

    def test_append_input_options(self):
        """Test method ShellCommand.append_input_options().
        """
        # input_options should be [] initially
        self.assertEqual(self.command.input_options, [])
        # append [] => []
        self.command.append_input_options([])
        self.assertEqual(self.command.input_options, [])
        # append ["foo"] => ["foo"]
        self.command.append_input_options(["foo"])
        self.assertEqual(self.command.input_options, ["foo"])
        # append ["bar"] => ["foo", "bar"]
        self.command.append_input_options(["bar"])
        self.assertEqual(self.command.input_options, ["foo", "bar"])
        # append ["baz", 42] => ["foo", "bar", "baz", 42]
        self.command.append_input_options(["baz", 42])
        self.assertEqual(
            self.command.input_options, ["foo", "bar", "baz", 42])

    def test_prepend_input_options(self):
        """Test method ShellCommand.prepend_input_options().
        """
        # input_options should be [] initially
        self.assertEqual(self.command.input_options, [])
        # prepend [] => []
        self.command.prepend_input_options([])
        self.assertEqual(self.command.input_options, [])
        # prepend ["foo"] => ["foo"]
        self.command.prepend_input_options(["foo"])
        self.assertEqual(self.command.input_options, ["foo"])
        # prepend ["bar"] => ["bar", "foo"]
        self.command.prepend_input_options(["bar"])
        self.assertEqual(self.command.input_options, ["bar", "foo"])
        # prepend ["baz", 42] => ["baz", 42, "bar", "foo"]
        self.command.prepend_input_options(["baz", 42])
        self.assertEqual(
            self.command.input_options, ["baz", 42, "bar", "foo"])

    def test_append_output_options(self):
        """Test method ShellCommand.append_output_options().
        """
        # output_options should be [] initially
        self.assertEqual(self.command.output_options, [])
        # append [] => []
        self.command.append_output_options([])
        self.assertEqual(self.command.output_options, [])
        # append ["foo"] => ["foo"]
        self.command.append_output_options(["foo"])
        self.assertEqual(self.command.output_options, ["foo"])
        # append ["bar"] => ["foo", "bar"]
        self.command.append_output_options(["bar"])
        self.assertEqual(self.command.output_options, ["foo", "bar"])
        # append ["baz", 42] => ["foo", "bar", "baz", 42]
        self.command.append_output_options(["baz", 42])
        self.assertEqual(
            self.command.output_options, ["foo", "bar", "baz", 42])

    def test_prepend_output_options(self):
        """Test method ShellCommand.prepend_output_options.
        """
        # output_options should be [] initially
        self.assertEqual(self.command.output_options, [])
        # prepend [] => []
        self.command.prepend_output_options([])
        self.assertEqual(self.command.output_options, [])
        # prepend ["foo"] => ["foo"]
        self.command.prepend_output_options(["foo"])
        self.assertEqual(self.command.output_options, ["foo"])
        # prepend ["bar"] => ["bar", "foo"]
        self.command.prepend_output_options(["bar"])
        self.assertEqual(self.command.output_options, ["bar", "foo"])
        # prepend ["baz", 42] => ["baz", 42, "bar", "foo"]
        self.command.prepend_output_options(["baz", 42])
        self.assertEqual(
            self.command.output_options, ["baz", 42, "bar", "foo"])

    def test_executable_string(self):
        """Test method ShellCommand.executable_string().
        """
        # Always "" in the base class.
        self.assertEqual(self.command.executable_string(quote=False), "")
        self.assertEqual(self.command.executable_string(quote=True), "")

    def test_argument_string(self):
        """Test method ShellCommand.argument_string().
        """
        # Always "" in the base class.
        self.assertEqual(self.command.argument_string(quote=False), "")
        self.assertEqual(self.command.argument_string(quote=True), "")

    def test_argument_list(self):
        """Test method ShellCommand.argument_list().
        """
        # Always [] in the base class.
        self.assertEqual(self.command.argument_list(), [])

    def test_command_string(self):
        """Test method ShellCommand.command_string().
        """
        # Always " " in the base class.
        self.assertEqual(self.command.command_string(quote=False), " ")
        # Subtlety: command_string() passes the quote argument on to
        # executable_string() and argument_string(). Thus, the result
        # should be " " regardless of the value of quote.
        self.assertEqual(self.command.command_string(quote=True), " ")
        # Add an option that needs to be quoted.
        self.command.append_output_options(["argle bargle"])
        self.assertEqual(
            self.command.command_string(quote=True), ' "argle bargle"')

    def test_process_pattern(self):
        """ Test method ShellCommand.process_pattern().
        """
        # True on EOF (0)
        self.assertTrue(self.command.process_pattern(0))
        # False on anythingthing else
        self.assertFalse(self.command.process_pattern(1))
        self.assertFalse(self.command.process_pattern(-1))
        self.assertFalse(self.command.process_pattern(None))

    # The following two will require mocking of pexpect?
    def test_run(self):
        """Test method ShellCommand.run().
        """
        pass

    def test_get_output(self):
        """Test method ShellCommand.get_output().
        """
        pass
