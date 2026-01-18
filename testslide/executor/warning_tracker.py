# Copyright (c) Facebook, Inc. and its affiliates.
# Copyright (c) Maifee Ul Asad <maifeeulasad@gmail.com>
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
Warning tracking for --fail-if-warning support.
Captures warnings during test import, execution, and shutdown phases.
"""

import fnmatch
import os
import warnings
from dataclasses import dataclass
from typing import Any


@dataclass
class CapturedWarning:
    """Represents a captured warning with its context."""

    message: str
    category: type[Warning]
    filename: str
    lineno: int
    line: str | None

    def __str__(self) -> str:
        return (
            f"{self.filename}:{self.lineno}: {self.category.__name__}: {self.message}"
        )


class WarningTracker:
    """
    Tracks warnings issued during test execution.
    Supports filtering warnings by file path patterns.
    """

    def __init__(
        self,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        """
        Initialize warning tracker.

        Args:
            include_patterns: List of glob patterns for files to include warnings from.
                             If None or empty, includes all files.
            exclude_patterns: List of glob patterns for files to exclude warnings from.
                             Takes precedence over include_patterns.
        """
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.captured_warnings: list[CapturedWarning] = []
        self._original_showwarning: Any = None
        self._active = False

    def _should_track_warning(self, filename: str) -> bool:
        """
        Determine if a warning from the given file should be tracked.

        Args:
            filename: Absolute path to the file that issued the warning.

        Returns:
            True if the warning should be tracked, False otherwise.
        """
        # Normalize path
        filename = os.path.abspath(filename)

        # Check exclude patterns first (they take precedence)
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(filename, pattern) or pattern in filename:
                return False

        # If no include patterns specified, include all (except excluded)
        if not self.include_patterns:
            return True

        # Check include patterns
        for pattern in self.include_patterns:
            if fnmatch.fnmatch(filename, pattern) or pattern in filename:
                return True

        return False

    def _custom_showwarning(
        self,
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file: Any = None,
        line: str | None = None,
    ) -> None:
        """
        Custom warning handler that captures warnings.
        """
        if self._should_track_warning(filename):
            captured = CapturedWarning(
                message=str(message),
                category=category,
                filename=filename,
                lineno=lineno,
                line=line,
            )
            self.captured_warnings.append(captured)

        # Also call the original showwarning to maintain normal warning behavior
        if self._original_showwarning:
            self._original_showwarning(message, category, filename, lineno, file, line)

    def start(self) -> None:
        """Start tracking warnings."""
        if self._active:
            return

        self._active = True
        self._original_showwarning = warnings.showwarning
        warnings.showwarning = self._custom_showwarning

        # Ensure all warnings are shown (not just once)
        warnings.simplefilter("always")

    def stop(self) -> None:
        """Stop tracking warnings and restore original warning handler."""
        if not self._active:
            return

        self._active = False
        if self._original_showwarning:
            warnings.showwarning = self._original_showwarning
            self._original_showwarning = None

    def get_warnings(self) -> list[CapturedWarning]:
        """Get all captured warnings."""
        return self.captured_warnings.copy()

    def has_warnings(self) -> bool:
        """Check if any warnings were captured."""
        return len(self.captured_warnings) > 0

    def clear(self) -> None:
        """Clear all captured warnings."""
        self.captured_warnings.clear()

    def __enter__(self) -> "WarningTracker":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()
