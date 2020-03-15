# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


def test_pass(testdir):
    testdir.makepyfile(
        """
		import pytest_testslide

		def test_has_mock_callable(testslide):
			testslide.mock_callable

		def test_mock_callable_assertion_works(testslide):
			testslide.mock_callable

		def test_mock_callable_unpaches(testslide):
			testslide.mock_callable

		def test_has_mock_async_callable(testslide):
			testslide.mock_async_callable

		def test_mock_async_callable_assertion_works(testslide):
			testslide.mock_async_callable

		def test_mock_async_callable_unpaches(testslide):
			testslide.mock_async_callable

		def test_has_mock_constructor(testslide):
			testslide.mock_constructor

		def test_mock_constructor_assertion_works(testslide):
			testslide.mock_constructor

		def test_mock_constructor_unpaches(testslide):
			testslide.mock_constructor

		def test_has_patch_attribute(testslide):
			testslide.patch_attribute

		def test_patch_attribute_unpaches(testslide):
			testslide.patch_attribute
		"""
    )
    result = testdir.runpytest("-v")
    assert "11 passed" in result.stdout.str()
    assert result.ret == 0
