import unittest

from shell_command import ShellCommand
from test_shared import ShellCommandSharedTestCase


class ShellCommandTestCase(ShellCommandSharedTestCase):
    """Test the ShellCommand class."""

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

    def test_shellquote(self):
        """Test shell quoting (static method)."""
        with self.subTest(msg="None ⇒ None"):
            self.assertIsNone(ShellCommand.shellquote(None))
        with self.subTest(msg='(empty string) ⇒ (empty string)'):
            self.assertEqual(ShellCommand.shellquote(""), "")
        with self.subTest(msg='␢ ⇒ " "'):
            self.assertEqual(ShellCommand.shellquote(" "), '" "')
        with self.subTest(msg='␢␢␢␢␢ ⇒ "     "'):
            self.assertEqual(ShellCommand.shellquote("     "), '"     "')
        with self.subTest(msg='foobar ⇒ foobar'):
            self.assertEqual(ShellCommand.shellquote("foobar"), "foobar")
        with self.subTest(msg='foo bar ⇒ "foo bar"'):
            self.assertEqual(
                ShellCommand.shellquote("foo bar"), '"foo bar"')
        with self.subTest(msg='"foobar" ⇒ \'"foobar"\''):
            self.assertEqual(
                ShellCommand.shellquote('"foobar"'), '\'"foobar"\'')
        with self.subTest(msg="'foobar' ⇒ 'foobar'"):
            self.assertEqual(
                ShellCommand.shellquote("'foobar'"), "'foobar'")
        with self.subTest(msg="foo 'bar' ⇒ \"foo 'bar'\""):
            self.assertEqual(
                ShellCommand.shellquote("foo 'bar'"), '"foo \'bar\'"')
        with self.subTest(msg='foo"bar ⇒ \'foo"bar\''):
            self.assertEqual(
                ShellCommand.shellquote('foo"bar'), '\'foo"bar\'')
        with self.subTest(msg='foo.bar ⇒ "foo.bar"'):
            self.assertEqual(ShellCommand.shellquote("foo.bar"), '"foo.bar"')
        with self.subTest(msg='foo(bar) ⇒ "foo(bar)"'):
            self.assertEqual(
                ShellCommand.shellquote("foo(bar)"), '"foo(bar)"')
        with self.subTest(msg='[foobar] ⇒ "[foobar]"'):
            self.assertEqual(
                ShellCommand.shellquote("[foobar]"), '"[foobar]"')
        with self.subTest(msg='foo[bar ⇒ "foo[bar"'):
            self.assertEqual(ShellCommand.shellquote("foo[bar"), '"foo[bar"')
        with self.subTest(msg="/foo/bar ⇒ /foo/bar"):
            self.assertEqual(ShellCommand.shellquote("/foo/bar"), "/foo/bar")
        with self.subTest(msg="-f ⇒ -f"):
            self.assertEqual(ShellCommand.shellquote("-f"), "-f")
        with self.subTest(msg="-foobar ⇒ -foobar"):
            self.assertEqual(ShellCommand.shellquote("--foobar"), "--foobar")
        with self.subTest(msg=r"( ⇒ \("):
            self.assertEqual(ShellCommand.shellquote("("), r"\(")
        with self.subTest(msg=r") ⇒ \)"):
            self.assertEqual(ShellCommand.shellquote(")"), r"\)")
        # ' => "'"
        with self.subTest(msg='\' ⇒ "\'"'):
            self.assertEqual(ShellCommand.shellquote("'"), '"\'"')

    def test_append_input_options(self):
        """Test appending to input options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.input_options, [])
        with self.subTest(msg="appending [] ⇒ []"):
            self.command.append_input_options([])
            self.assertEqual(self.command.input_options, [])
        with self.subTest(msg='appending ["foo"] ⇒ ["foo"]'):
            self.command.append_input_options(["foo"])
            self.assertEqual(self.command.input_options, ["foo"])
        with self.subTest(msg='appending ["bar"] ⇒ ["foo", "bar"]'):
            self.command.append_input_options(["bar"])
            self.assertEqual(self.command.input_options, ["foo", "bar"])
        with self.subTest(
                msg='appending ["baz", 42] ⇒ ["foo", "bar", "baz", 42]'):
            self.command.append_input_options(["baz", 42])
            self.assertEqual(
                self.command.input_options, ["foo", "bar", "baz", 42])

    def test_prepend_input_options(self):
        """Test prepending to input options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.input_options, [])
        with self.subTest(msg="prepending [] ⇒ []"):
            self.command.prepend_input_options([])
            self.assertEqual(self.command.input_options, [])
        with self.subTest(msg='prepending ["foo"] ⇒ ["foo"]'):
            self.command.prepend_input_options(["foo"])
            self.assertEqual(self.command.input_options, ["foo"])
        with self.subTest(msg='prepending ["bar"] ⇒ ["bar", "foo"]'):
            self.command.prepend_input_options(["bar"])
            self.assertEqual(self.command.input_options, ["bar", "foo"])
        with self.subTest(
                msg='prepending ["baz", 42] ⇒ ["baz", 42, "bar", "foo]'):
            self.command.prepend_input_options(["baz", 42])
            self.assertEqual(
                self.command.input_options, ["baz", 42, "bar", "foo"])

    def test_append_output_options(self):
        """Test appending to output options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.output_options, [])
        with self.subTest(msg="appending [] ⇒ []"):
            self.command.append_output_options([])
            self.assertEqual(self.command.output_options, [])
        with self.subTest(msg='appending ["foo"] ⇒ ["foo"]'):
            self.command.append_output_options(["foo"])
            self.assertEqual(self.command.output_options, ["foo"])
        with self.subTest(msg='appending ["bar"] ⇒ ["foo", "bar"]'):
            self.command.append_output_options(["bar"])
            self.assertEqual(self.command.output_options, ["foo", "bar"])
        with self.subTest(
                msg='appending ["baz", 42] ⇒ ["foo", "bar", "baz", 42]'):
            self.command.append_output_options(["baz", 42])
            self.assertEqual(
                self.command.output_options, ["foo", "bar", "baz", 42])

    def test_prepend_output_options(self):
        """Test prepending to output options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.output_options, [])
        with self.subTest(msg="prepending [] ⇒ []"):
            self.command.prepend_output_options([])
            self.assertEqual(self.command.output_options, [])
        with self.subTest(msg='prepending ["foo"] ⇒ ["foo"]'):
            self.command.prepend_output_options(["foo"])
            self.assertEqual(self.command.output_options, ["foo"])
        with self.subTest(msg='prepending ["bar"] ⇒ ["bar", "foo"]'):
            self.command.prepend_output_options(["bar"])
            self.assertEqual(self.command.output_options, ["bar", "foo"])
        with self.subTest(
                msg='prepending ["baz", 42] ⇒ ["baz", 42, "bar", "foo]'):
            self.command.prepend_output_options(["baz", 42])
            self.assertEqual(
                self.command.output_options, ["baz", 42, "bar", "foo"])

    def test_process_pattern(self):
        """ Test pattern processing."""
        # True on EOF (0)
        with self.subTest(msg="returns True on EOF"):
            self.assertTrue(self.command.process_pattern(0))
        # False on anythingthing else
        with self.subTest(msg="returns False on 1"):
            self.assertFalse(self.command.process_pattern(1))
        with self.subTest(msg="returns False on -1"):
            self.assertFalse(self.command.process_pattern(-1))
        with self.subTest(msg="returns False on None"):
            self.assertFalse(self.command.process_pattern(None))

    # The following two will require mocking of pexpect?
    def test_run(self):
        """Test running of subprocess."""
        pass

    def test_get_output(self):
        """Test getting output from subprocess."""
        pass


# Remove ShellCommandSharedTestCase from the namespace so we don't run
# the shared tests twice. See <https://stackoverflow.com/a/22836015>.
del(ShellCommandSharedTestCase)
