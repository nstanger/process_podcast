import unittest

from shell_command import ShellCommand
from test_shared import ShellCommandSharedTestCase


class ShellCommandTestCase(ShellCommandSharedTestCase):
    """Test the ShellCommand class.
    """

    def setUp(self):
        """Initialisation. Make sure the input and output options are
        explicitly set to [] otherwise they hang around from previous
        tests.
        """
        self.command = ShellCommand(input_options=[], output_options=[])
        self.expected_executable = ""
        self.expected_base_options = []
        self.expected_input_options = []
        self.expected_filter_options = []
        self.expected_output_options = []

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


# Remove ShellCommandSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(ShellCommandSharedTestCase)
