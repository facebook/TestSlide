# pyre-unsafe
import unittest
from typing import Any

from testslide.bdd.lib import *
from testslide.bdd.lib import Context  # noqa
from testslide.core import _importer  # noqa

#  `testslide.executor.lib`.
from testslide.executor.lib import *

from testslide.strict_mock import StrictMock as StrictMock  # noqa

class TestCase(unittest.TestCase):  # type: ignore
    def setUp(self) -> None: ...
    @staticmethod
    def mock_callable(*args, **kwargs): ...  # incomplete
    @staticmethod
    def mock_async_callable(*args, **kwargs): ...  # incomplete
    @staticmethod
    def mock_constructor(*args, **kwargs): ...  # incomplete
    @staticmethod
    def patch_attribute(*args, **kwargs): ...  # incomplete

_ContextData = Any
