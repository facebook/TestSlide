# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import re


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
			sample_module.CallOrderTarget("c").f1("a")
		"""
    )
    result = testdir.runpytest("-v")
    assert "12 passed, 1 error" in result.stdout.str()
    expected_failure = re.compile(
        """.*_______________ ERROR at teardown of test_aggregated_exceptions ________________
2 failures.
<class \'AssertionError\'>: calls did not match assertion.
<StrictMock 0x[a-fA-F0-9]+ template=tests.sample_module.CallOrderTarget .*/test_pass0/test_pass.py:39>, \'f1\':
  expected: called exactly 1 time\(s\) with arguments:
    \(\'a\',\)
  received: 0 call\(s\)
<class \'AssertionError\'>: calls did not match assertion.
<StrictMock 0x[a-fA-F0-9]+ template=tests.sample_module.CallOrderTarget .*/test_pass0/test_pass.py:39>, \'f1\':
  expected: called exactly 1 time\(s\) with arguments:
    \(\'b\',\)
  received: 0 call\(s\).*""",
        re.MULTILINE | re.DOTALL,
    )
    assert expected_failure.match(result.stdout.str())
    assert result.ret != 0
