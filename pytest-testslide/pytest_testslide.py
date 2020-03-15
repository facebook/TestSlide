# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import pytest
import testslide as testslide_module


class _TestSlideFixture:
    def _register_assertion(self, assertion):
        self._assertions.append(assertion)

    def __enter__(self):
        self._assertions = []
        testslide_module.mock_callable.register_assertion = self._register_assertion
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            # FIXME aggregated failures
            for assertion in self._assertions:
                assertion()
        finally:
            testslide_module.mock_callable.unpatch_all_callable_mocks
            testslide_module.mock_constructor.unpatch_all_constructor_mocks
            testslide_module.patch_attribute.unpatch_all_mocked_attributes

    @staticmethod
    def mock_callable(*args, **kwargs):
        return testslide_module.mock_callable.mock_callable(*args, **kwargs)

    @staticmethod
    def mock_async_callable(*args, **kwargs):
        return testslide_module.mock_callable.mock_async_callable(*args, **kwargs)

    @staticmethod
    def mock_constructor(*args, **kwargs):
        return testslide_module.mock_constructor.mock_constructor(*args, **kwargs)

    @staticmethod
    def patch_attribute(*args, **kwargs):
        return testslide_module.patch_attribute.patch_attribute(*args, **kwargs)


@pytest.fixture
def testslide():
    with _TestSlideFixture() as testslide_fixture:
        yield testslide_fixture
