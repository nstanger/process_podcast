import unittest

from shell_command import ShellCommand
from shell_command.tests import ShellCommandSharedTestCase


class ShellCommandTestCase(ShellCommandSharedTestCase):
    """Test the ShellCommand class."""

    def test_shellquote(self):
        """Test shell quoting (static method)."""
        test_data = (
            (None, None, "None ⇒ None"),
            ("", "", "(empty string) ⇒ (empty string)"),
            (" ", '" "', '␢ ⇒ " "'),
            ("     ", '"     "', '␢␢␢␢␢ ⇒ "     "'),
            ("foobar", "foobar", "foobar ⇒ foobar"),
            ("foo bar", '"foo bar"', 'foo bar ⇒ "foo bar"'),
            ('"foobar"', '\'"foobar"\'', '"foobar" ⇒ \'"foobar"\''),
            ("'foobar'", "'foobar'", "'foobar' ⇒ 'foobar'"),
            ("foo 'bar'", '"foo \'bar\'"', "foo 'bar' ⇒ \"foo 'bar'\""),
            ('foo"bar', '\'foo"bar\'', 'foo"bar ⇒ \'foo"bar\''),
            ("foo.bar", '"foo.bar"', 'foo.bar ⇒ "foo.bar"'),
            ("foo(bar)", '"foo(bar)"', 'foo(bar) ⇒ "foo(bar)"'),
            ("[foobar]", '"[foobar]"', '[foobar] ⇒ "[foobar]"'),
            ("foo[bar", '"foo[bar"', 'foo[bar ⇒ "foo[bar"'),
            ("/foo/bar", "/foo/bar", "/foo/bar ⇒ /foo/bar"),
            ("-f", "-f", "-f ⇒ -f"),
            ("--foobar", "--foobar", "--foobar ⇒ --foobar"),
            ("(", r"\(", r"( ⇒ \("),
            (")", r"\)", r"( ⇒ \)"),
            ("'", '"\'"', '\' ⇒ "\'"'),
        )
        for original, expected, description in test_data:
            with self.subTest(msg=description):
                self.assertEqual(ShellCommand.shellquote(original), expected)

    def test_append_input_options(self):
        """Test appending to input options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.input_options, [])
        test_data = (
            ([], [], "[] ⇒ []"),
            (["foo"], ["foo"], '["foo"] ⇒ ["foo"]'),
            (["bar"], ["foo", "bar"], '["bar"] ⇒ ["foo", "bar"]'),
            (["baz", 42], ["foo", "bar", "baz", 42],
             '["baz", 42] ⇒ ["foo", "bar", "baz", 42]'),
        )
        for appended, expected, description in test_data:
            with self.subTest(msg="appending {}".format(description)):
                self.command.append_input_options(appended)
                self.assertEqual(self.command.input_options, expected)

    def test_prepend_input_options(self):
        """Test prepending to input options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.input_options, [])
        test_data = (
            ([], [], "[] ⇒ []"),
            (["foo"], ["foo"], '["foo"] ⇒ ["foo"]'),
            (["bar"], ["bar", "foo"], '["bar"] ⇒ ["bar", "foo"]'),
            (["baz", 42], ["baz", 42, "bar", "foo"],
             '["baz", 42] ⇒ ["baz", 42, "bar", "foo"]'),
        )
        for prepended, expected, description in test_data:
            with self.subTest(msg="prepending {}".format(description)):
                self.command.prepend_input_options(prepended)
                self.assertEqual(self.command.input_options, expected)

    def test_append_output_options(self):
        """Test appending to output options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.output_options, [])
        test_data = (
            ([], [], "[] ⇒ []"),
            (["foo"], ["foo"], '["foo"] ⇒ ["foo"]'),
            (["bar"], ["foo", "bar"], '["bar"] ⇒ ["foo", "bar"]'),
            (["baz", 42], ["foo", "bar", "baz", 42],
             '["baz", 42] ⇒ ["foo", "bar", "baz", 42]'),
        )
        for appended, expected, description in test_data:
            with self.subTest(msg="appending {}".format(description)):
                self.command.append_output_options(appended)
                self.assertEqual(self.command.output_options, expected)

    def test_prepend_output_options(self):
        """Test prepending to output options."""
        with self.subTest(msg="should initially be []"):
            self.assertEqual(self.command.output_options, [])
        test_data = (
            ([], [], "[] ⇒ []"),
            (["foo"], ["foo"], '["foo"] ⇒ ["foo"]'),
            (["bar"], ["bar", "foo"], '["bar"] ⇒ ["bar", "foo"]'),
            (["baz", 42], ["baz", 42, "bar", "foo"],
             '["baz", 42] ⇒ ["baz", 42, "bar", "foo"]'),
        )
        for prepended, expected, description in test_data:
            with self.subTest(msg="prepending {}".format(description)):
                self.command.prepend_output_options(prepended)
                self.assertEqual(self.command.output_options, expected)

    # This test should really be shared (i.e., in __init__.py),
    # but we can't do that until we figure out how to properly test
    # FFmpegConcatCommand.process_pattern().
    def test_process_pattern(self):
        """ Test pattern processing."""
        # True on EOF (0)
        with self.subTest(msg="returns True on EOF"):
            self.assertTrue(self.command.process_pattern(0))
        # False on anything else
        for i in (x for x in range(-1000, 1001) if x is not 0):
            with self.subTest(msg="returns False on {}".format(i)):
                self.assertFalse(self.command.process_pattern(i))

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
