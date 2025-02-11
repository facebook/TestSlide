# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-unsafe

from collections.abc import Callable, Iterator
from types import TracebackType
from typing import Any

import pytest

import testslide as testslide_module


class _TestSlideFixture:
    def _register_assertion(self, assertion: Callable) -> None:
        # pyre-fixme[16]: `_TestSlideFixture` has no attribute `_assertions`.
        self._assertions.append(assertion)

    def __enter__(self) -> "_TestSlideFixture":
        # pyre-fixme[16]: `_TestSlideFixture` has no attribute `_assertions`.
        self._assertions: list[Callable] = []
        testslide_module.mock_callable.register_assertion = self._register_assertion
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: TracebackType,
    ):
        # pyre-fixme[16]: Module `lib` has no attribute `AggregatedExceptions`.
        aggregated_exceptions = testslide_module.bdd.lib.AggregatedExceptions()
        try:
            # pyre-fixme[16]: `_TestSlideFixture` has no attribute `_assertions`.
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
    ) -> testslide_module.core.mock_callable._MockAsyncCallableDSL:
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
