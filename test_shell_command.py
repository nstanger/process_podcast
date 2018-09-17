import unittest

from shell_command import (
    ShellCommand, ConvertCommand, FFmpegConcatCommand, FFprobeCommand
)


class TestShellCommand(unittest.TestCase):
    """Test the ShellCommand class.
    """

    def setUp(self):
        """Test initialisation.
        """
        self.command = ShellCommand()

    def tearDown(self):
        """Test cleanup.
        """
        del(self.command)

    def test_shellquote(self):
        """Test static method ShellCommand.shellquote().
        """
        # empty => empty
        self.assertEqual(ShellCommand.shellquote(""), "")
        # foobar => foobar
        self.assertEqual(ShellCommand.shellquote("foobar"), "foobar")
        # foo bar => "foo bar"
        self.assertEqual(ShellCommand.shellquote("foo bar"), '"foo bar"')
        # "foobar" => '"foobar"'
        self.assertEqual(ShellCommand.shellquote('"foobar"'), '\'"foobar"\'')
        # 'foobar' => 'foobar'
        self.assertEqual(ShellCommand.shellquote("'foobar'"), "'foobar'")
        # foo 'bar' => "foo 'bar'"
        self.assertEqual(ShellCommand.shellquote("foo 'bar'"), '"foo \'bar\'"')
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
        """Test method ShellCommand.append_input_options.
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
        self.assertEqual(self.command.input_options, ["foo", "bar", "baz", 42])

    def test_prepend_input_options(self):
        """Test method ShellCommand.prepend_input_options.
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
        self.assertEqual(self.command.input_options, ["baz", 42, "bar", "foo"])
