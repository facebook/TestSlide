# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from types import TracebackType
from typing import Any, Callable, Iterator, List, Optional

import pytest

import testslide as testslide_module


class _TestSlideFixture:
    def _register_assertion(self, assertion: Callable) -> None:
        self._assertions.append(assertion)

    def __enter__(self) -> "_TestSlideFixture":
        self._assertions: List[Callable] = []
        testslide_module.mock_callable.register_assertion = self._register_assertion
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: TracebackType,
    ):
        aggregated_exceptions = testslide_module.AggregatedExceptions()
        try:
            for assertion in self._assertions:
                try:
                    assertion()
                except BaseException as be:
                    aggregated_exceptions.append_exception(be)

        finally:
            testslide_module.mock_callable.unpatch_all_callable_mocks()
            testslide_module.mock_constructor.unpatch_all_constructor_mocks()
            testslide_module.patch_attribute.unpatch_all_mocked_attributes()
        if aggregated_exceptions.exceptions:
            pytest.fail(str(aggregated_exceptions), False)

    @staticmethod
    def mock_callable(
        *args: Any, **kwargs: Any
    ) -> testslide_module.mock_callable._MockCallableDSL:
        return testslide_module.mock_callable.mock_callable(*args, **kwargs)

    @staticmethod
    def mock_async_callable(
        *args: Any, **kwargs: Any
    ) -> testslide_module.mock_callable._MockAsyncCallableDSL:
        return testslide_module.mock_callable.mock_async_callable(*args, **kwargs)

    @staticmethod
    def mock_constructor(
        *args: Any, **kwargs: Any
    ) -> testslide_module.mock_constructor._MockConstructorDSL:
        return testslide_module.mock_constructor.mock_constructor(*args, **kwargs)

    @staticmethod
    def patch_attribute(*args: Any, **kwargs: Any) -> None:
        return testslide_module.patch_attribute.patch_attribute(*args, **kwargs)


@pytest.fixture
def testslide() -> Iterator[_TestSlideFixture]:
    with _TestSlideFixture() as testslide_fixture:
        yield testslide_fixture
