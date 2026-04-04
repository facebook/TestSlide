# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
Integration tests for --fail-if-warning CLI flag.
"""

import os
import subprocess
import sys
import tempfile
from unittest import TestCase


class TestFailIfWarningIntegration(TestCase):
    """Integration tests for the --fail-if-warning feature."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.python = sys.executable
        self.testslide_cli = [self.python, "-m", "testslide.executor.cli"]
        # Get the TestSlide project root (parent of tests directory)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Set up environment with PYTHONPATH so testslide can be imported
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = self.project_root

    def _write_test_file(self, filename, content):
        """Helper to write a test file."""
        filepath = os.path.join(self.test_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def test_fails_when_warning_issued_during_test(self):
        """Test that --fail-if-warning causes failure when warning is issued."""
        test_file = self._write_test_file(
            "test_with_warning.py",
            """
import warnings
from testslide import TestCase

class TestWithWarning(TestCase):
    def test_issues_warning(self):
        warnings.warn("This is a test warning", UserWarning)
        self.assertTrue(True)
""",
        )

        result = subprocess.run(
            self.testslide_cli + ["--fail-if-warning", test_file],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, "Expected non-zero exit code")
        self.assertIn("WARNINGS DETECTED", output)
        self.assertIn("This is a test warning", output)
        self.assertIn("Total warnings: 1", output)

    def test_passes_when_no_warning_issued(self):
        """Test that --fail-if-warning passes when no warnings are issued."""
        test_file = self._write_test_file(
            "test_without_warning.py",
            """
from testslide import TestCase

class TestWithoutWarning(TestCase):
    def test_no_warning(self):
        self.assertTrue(True)
""",
        )

        result = subprocess.run(
            self.testslide_cli + ["--fail-if-warning", test_file],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        self.assertEqual(
            result.returncode, 0, f"Expected zero exit code. Output: {output}"
        )
        self.assertNotIn("WARNINGS DETECTED", output)

    def test_warning_include_path_filters_correctly(self):
        """Test that --warning-include-path filters warnings correctly."""
        # Create a test file that issues a warning
        test_file = self._write_test_file(
            "my_test.py",
            """
import warnings
from testslide import TestCase

class MyTest(TestCase):
    def test_with_warning(self):
        warnings.warn("Test warning", UserWarning)
        self.assertTrue(True)
""",
        )

        # Run with include pattern that matches the test file
        result = subprocess.run(
            self.testslide_cli
            + [
                "--fail-if-warning",
                f"--warning-include-path=*{os.sep}my_test.py",
                test_file,
            ],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WARNINGS DETECTED", output)

        # Run with include pattern that doesn't match
        result = subprocess.run(
            self.testslide_cli
            + [
                "--fail-if-warning",
                f"--warning-include-path=*{os.sep}other_test.py",
                test_file,
            ],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        # Should pass because warning doesn't match include pattern
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("WARNINGS DETECTED", output)

    def test_warning_exclude_path_filters_correctly(self):
        """Test that --warning-exclude-path filters warnings correctly."""
        test_file = self._write_test_file(
            "excluded_test.py",
            """
import warnings
from testslide import TestCase

class ExcludedTest(TestCase):
    def test_with_warning(self):
        warnings.warn("Test warning", UserWarning)
        self.assertTrue(True)
""",
        )

        # Run with exclude pattern that matches the test file
        result = subprocess.run(
            self.testslide_cli
            + [
                "--fail-if-warning",
                f"--warning-exclude-path=*{os.sep}excluded_test.py",
                test_file,
            ],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        # Should pass because warning is excluded
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("WARNINGS DETECTED", output)

    def test_multiple_warnings_are_all_reported(self):
        """Test that all warnings are reported."""
        test_file = self._write_test_file(
            "test_multiple_warnings.py",
            """
import warnings
from testslide import TestCase

class TestMultipleWarnings(TestCase):
    def test_first_warning(self):
        warnings.warn("Warning 1", UserWarning)
        self.assertTrue(True)
    
    def test_second_warning(self):
        warnings.warn("Warning 2", DeprecationWarning)
        self.assertTrue(True)
""",
        )

        result = subprocess.run(
            self.testslide_cli + ["--fail-if-warning", test_file],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WARNINGS DETECTED", output)
        self.assertIn("Warning 1", output)
        self.assertIn("Warning 2", output)
        self.assertIn("Total warnings: 2", output)

    def test_warning_during_import(self):
        """Test that warnings during module import are caught."""
        test_file = self._write_test_file(
            "test_import_warning.py",
            """
import warnings

# Warning at module level (during import)
warnings.warn("Warning during import", UserWarning)

from testslide import TestCase

class TestImportWarning(TestCase):
    def test_something(self):
        self.assertTrue(True)
""",
        )

        result = subprocess.run(
            self.testslide_cli + ["--fail-if-warning", test_file],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WARNINGS DETECTED", output)
        self.assertIn("Warning during import", output)

    def test_works_without_fail_if_warning_flag(self):
        """Test that warnings don't cause failure without the flag."""
        test_file = self._write_test_file(
            "test_warning_no_flag.py",
            """
import warnings
from testslide import TestCase

class TestWarningNoFlag(TestCase):
    def test_with_warning(self):
        warnings.warn("This warning should be ignored", UserWarning)
        self.assertTrue(True)
""",
        )

        # Run WITHOUT --fail-if-warning flag
        result = subprocess.run(
            self.testslide_cli + [test_file],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.test_dir,
        )

        output = result.stdout + result.stderr
        # Should pass even though warning was issued
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("WARNINGS DETECTED", output)
