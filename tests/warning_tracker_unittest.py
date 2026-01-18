# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
Tests for the warning tracker functionality.
"""

import os
import tempfile
import warnings
from unittest import TestCase

from testslide.executor.warning_tracker import CapturedWarning, WarningTracker


class TestWarningTracker(TestCase):
    """Test the WarningTracker class."""

    def test_captures_warnings(self):
        """Test that warnings are captured."""
        tracker = WarningTracker()
        tracker.start()

        warnings.warn("Test warning 1", UserWarning)
        warnings.warn("Test warning 2", DeprecationWarning)

        tracker.stop()

        captured = tracker.get_warnings()
        self.assertEqual(len(captured), 2)
        self.assertIn("Test warning 1", captured[0].message)
        self.assertIn("Test warning 2", captured[1].message)

    def test_has_warnings_returns_true_when_warnings_exist(self):
        """Test has_warnings returns True when warnings are captured."""
        tracker = WarningTracker()
        tracker.start()

        warnings.warn("Test warning", UserWarning)

        tracker.stop()

        self.assertTrue(tracker.has_warnings())

    def test_has_warnings_returns_false_when_no_warnings(self):
        """Test has_warnings returns False when no warnings are captured."""
        tracker = WarningTracker()
        tracker.start()
        tracker.stop()

        self.assertFalse(tracker.has_warnings())

    def test_clear_removes_warnings(self):
        """Test that clear() removes all captured warnings."""
        tracker = WarningTracker()
        tracker.start()

        warnings.warn("Test warning", UserWarning)

        tracker.stop()

        self.assertTrue(tracker.has_warnings())
        tracker.clear()
        self.assertFalse(tracker.has_warnings())

    def test_include_pattern_filters_warnings(self):
        """Test that include patterns filter warnings correctly."""
        # Create temp files to simulate different source locations
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_file.py")
            other_file = os.path.join(tmpdir, "other_file.py")

            # Create files
            open(test_file, "w").close()
            open(other_file, "w").close()

            # Track only warnings from files matching pattern
            tracker = WarningTracker(include_patterns=[f"*{os.sep}test_*.py"])
            tracker.start()

            # This should be captured
            warnings.warn_explicit(
                "Warning from test file",
                UserWarning,
                test_file,
                10,
            )

            # This should NOT be captured (doesn't match pattern)
            warnings.warn_explicit(
                "Warning from other file",
                UserWarning,
                other_file,
                20,
            )

            tracker.stop()

            captured = tracker.get_warnings()
            self.assertEqual(len(captured), 1)
            self.assertIn("Warning from test file", captured[0].message)
            self.assertIn("test_file.py", captured[0].filename)

    def test_exclude_pattern_filters_warnings(self):
        """Test that exclude patterns filter warnings correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_file.py")
            vendor_file = os.path.join(tmpdir, "vendor_lib.py")

            open(test_file, "w").close()
            open(vendor_file, "w").close()

            # Exclude warnings from vendor files
            tracker = WarningTracker(exclude_patterns=[f"*{os.sep}vendor_*.py"])
            tracker.start()

            # This should be captured
            warnings.warn_explicit(
                "Warning from test file",
                UserWarning,
                test_file,
                10,
            )

            # This should NOT be captured (excluded)
            warnings.warn_explicit(
                "Warning from vendor file",
                UserWarning,
                vendor_file,
                20,
            )

            tracker.stop()

            captured = tracker.get_warnings()
            self.assertEqual(len(captured), 1)
            self.assertIn("Warning from test file", captured[0].message)

    def test_exclude_takes_precedence_over_include(self):
        """Test that exclude patterns take precedence over include patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "myproject_test.py")
            file2 = os.path.join(tmpdir, "myproject_lib.py")

            open(file1, "w").close()
            open(file2, "w").close()

            # Include myproject_* but exclude *_test.py
            tracker = WarningTracker(
                include_patterns=[f"*{os.sep}myproject_*.py"],
                exclude_patterns=[f"*{os.sep}*_test.py"],
            )
            tracker.start()

            # This should NOT be captured (excluded wins)
            warnings.warn_explicit(
                "Warning from test",
                UserWarning,
                file1,
                10,
            )

            # This should be captured
            warnings.warn_explicit(
                "Warning from lib",
                UserWarning,
                file2,
                20,
            )

            tracker.stop()

            captured = tracker.get_warnings()
            self.assertEqual(len(captured), 1)
            self.assertIn("Warning from lib", captured[0].message)

    def test_context_manager_protocol(self):
        """Test that WarningTracker works as a context manager."""
        with WarningTracker() as tracker:
            warnings.warn("Test warning", UserWarning)

        # After exiting context, tracker should be stopped
        captured = tracker.get_warnings()
        self.assertEqual(len(captured), 1)
        self.assertIn("Test warning", captured[0].message)

    def test_captures_different_warning_categories(self):
        """Test that different warning categories are captured correctly."""
        tracker = WarningTracker()
        tracker.start()

        warnings.warn("User warning", UserWarning)
        warnings.warn("Deprecation warning", DeprecationWarning)
        warnings.warn("Future warning", FutureWarning)
        warnings.warn("Runtime warning", RuntimeWarning)

        tracker.stop()

        captured = tracker.get_warnings()
        self.assertEqual(len(captured), 4)

        categories = [w.category for w in captured]
        self.assertIn(UserWarning, categories)
        self.assertIn(DeprecationWarning, categories)
        self.assertIn(FutureWarning, categories)
        self.assertIn(RuntimeWarning, categories)

    def test_captured_warning_str_representation(self):
        """Test CapturedWarning string representation."""
        warning = CapturedWarning(
            message="Test message",
            category=UserWarning,
            filename="/path/to/file.py",
            lineno=42,
            line=None,
        )

        result = str(warning)
        self.assertIn("/path/to/file.py", result)
        self.assertIn("42", result)
        self.assertIn("UserWarning", result)
        self.assertIn("Test message", result)

    def test_no_warnings_tracked_when_not_started(self):
        """Test that warnings are not tracked when tracker is not started."""
        tracker = WarningTracker()

        warnings.warn("Test warning", UserWarning)

        # Tracker was never started, so no warnings should be captured
        self.assertFalse(tracker.has_warnings())
        self.assertEqual(len(tracker.get_warnings()), 0)

    def test_substring_pattern_matching(self):
        """Test that substring patterns work for filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_file = os.path.join(tmpdir, "myproject", "module.py")
            vendor_file = os.path.join(tmpdir, "site-packages", "vendor.py")

            os.makedirs(os.path.dirname(project_file), exist_ok=True)
            os.makedirs(os.path.dirname(vendor_file), exist_ok=True)
            open(project_file, "w").close()
            open(vendor_file, "w").close()

            # Exclude anything with 'site-packages' in the path
            tracker = WarningTracker(exclude_patterns=["site-packages"])
            tracker.start()

            warnings.warn_explicit(
                "Project warning",
                UserWarning,
                project_file,
                10,
            )

            warnings.warn_explicit(
                "Vendor warning",
                UserWarning,
                vendor_file,
                20,
            )

            tracker.stop()

            captured = tracker.get_warnings()
            self.assertEqual(len(captured), 1)
            self.assertIn("Project warning", captured[0].message)
