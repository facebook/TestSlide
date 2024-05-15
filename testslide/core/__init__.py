# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os

if "COVERAGE_PROCESS_START" in os.environ:
    import coverage

    coverage.process_startup()

import os
import sys
import unittest
from typing import Any

from . import mock_callable as _mock_callable
from . import mock_constructor as _mock_constructor
from . import patch_attribute as _patch_attribute
from .strict_mock import StrictMock  # noqa

if sys.version_info < (3, 7):
    raise RuntimeError("Python >=3.7 required.")


def _importer(target: str) -> Any:
    components = target.split(".")
    import_path = components.pop(0)
    thing = __import__(import_path)

    def dot_lookup(thing: object, comp: str, import_path: str) -> Any:
        try:
            return getattr(thing, comp)
        except AttributeError:
            __import__(import_path)
            return getattr(thing, comp)

    for comp in components:
        import_path += ".%s" % comp
        thing = dot_lookup(thing, comp, import_path)
    return thing


class TestCase(unittest.TestCase):
    """
    A subclass of unittest.TestCase that adds TestSlide's features.
    """

    def setUp(self) -> None:
        _mock_callable.register_assertion = lambda assertion: self.addCleanup(assertion)
        self.addCleanup(_mock_callable.unpatch_all_callable_mocks)
        self.addCleanup(_mock_constructor.unpatch_all_constructor_mocks)
        self.addCleanup(_patch_attribute.unpatch_all_mocked_attributes)
        super(TestCase, self).setUp()

    @staticmethod
    def mock_callable(*args: Any, **kwargs: Any) -> _mock_callable._MockCallableDSL:
        return _mock_callable.mock_callable(*args, **kwargs)

    @staticmethod
    def mock_async_callable(
        *args: Any, **kwargs: Any
    ) -> _mock_callable._MockCallableDSL:
        return _mock_callable.mock_async_callable(*args, **kwargs)

    @staticmethod
    def mock_constructor(
        *args: Any, **kwargs: Any
    ) -> _mock_constructor._MockConstructorDSL:
        return _mock_constructor.mock_constructor(*args, **kwargs)

    @staticmethod
    def patch_attribute(*args: Any, **kwargs: Any) -> None:
        return _patch_attribute.patch_attribute(*args, **kwargs)
