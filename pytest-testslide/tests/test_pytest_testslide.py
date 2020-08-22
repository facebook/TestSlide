# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


def test_pass(testdir):
    testdir.makepyfile(
        """
		from pytest_testslide import testslide
		from tests import sample_module
		from testslide import StrictMock

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

		def test_aggregated_exceptions(testslide):
			mocked_cls = StrictMock(sample_module.CallOrderTarget)
			testslide.mock_callable(mocked_cls, 'f1')\
				.for_call("a").to_return_value("mocked")\
				.and_assert_called_once()
			testslide.mock_callable(mocked_cls, 'f1')\
				.for_call("b").to_return_value("mocked2")\
				.and_assert_called_once()
			assert sample_module.CallOrderTarget("a").f1("a") == "mocked"
		"""
    )
    result = testdir.runpytest("-v")
    assert "11 passed" in result.stdout.str()
    assert result.ret == 0
