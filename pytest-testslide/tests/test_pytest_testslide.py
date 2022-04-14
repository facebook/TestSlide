# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import re
import sys


def test_pass(testdir):
    testdir.makepyfile(
        """
        import time
        import pytest
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

        # mock_callable integration tests
        def test_mock_callable_patching_works(testslide):
            testslide.mock_callable(time, "sleep").to_raise(RuntimeError("Mocked!"))
            with pytest.raises(RuntimeError):
                time.sleep()

        def test_mock_callable_unpatching_works(testslide):
            # This will fail if unpatching from test_mock_callable_patching_works does
            # not happen
            time.sleep(0)

        def test_mock_callable_assertion_works(testslide):
            testslide.mock_callable("time", "sleep").for_call(0).to_call_original().and_assert_called_once()
            time.sleep(0)
        
        def test_mock_callable_failing_assertion_works(testslide):
            testslide.mock_callable("time", "sleep").for_call(0).to_call_original().and_assert_called_once()

        # mock_async_callable integration test
        @pytest.mark.asyncio
        async def test_mock_async_callable_patching_works(testslide):
            testslide.mock_async_callable(sample_module.ParentTarget, "async_static_method").to_raise(RuntimeError("Mocked!"))
            with pytest.raises(RuntimeError):
                await sample_module.ParentTarget.async_static_method("a", "b")

        @pytest.mark.asyncio
        async def test_mock_async_callable_unpatching_works(testslide):
            # This will fail if unpatching from test_mock_async_callable_patching_works does
            # not happen
            assert await sample_module.ParentTarget.async_static_method("a", "b") == ["async original response"]

        @pytest.mark.asyncio
        async def test_mock_async_callable_assertion_works(testslide):
            testslide.mock_async_callable(sample_module.ParentTarget, "async_static_method").for_call("a", "b").to_call_original().and_assert_called_once()
            await sample_module.ParentTarget.async_static_method("a", "b")

        def test_mock_async_callable_failing_assertion_works(testslide):
            testslide.mock_async_callable(sample_module.ParentTarget, "async_static_method").for_call("a", "b").to_call_original().and_assert_called_once()

        # mock_constructor integration test
        def test_mock_constructor_patching_works(testslide):
            testslide.mock_constructor(sample_module, "ParentTarget").to_raise(RuntimeError("Mocked!"))
            with pytest.raises(RuntimeError):
                sample_module.ParentTarget()

        def test_mock_constructor_unpatching_works(testslide):
            # This will fail if unpatching from test_mock_constructor_patching_works does
            # not happen
            assert sample_module.ParentTarget()

        def test_mock_constructor_assertion_works(testslide):
            testslide.mock_constructor(sample_module, "ParentTarget").to_call_original().and_assert_called_once()
            sample_module.ParentTarget()

        def test_mock_constructor_failing_assertion_works(testslide):
            testslide.mock_constructor(sample_module, "ParentTarget").to_call_original().and_assert_called_once()

        # patch_attribute integration test
        def test_patch_attribute_patching_works(testslide):
            testslide.patch_attribute(sample_module.SomeClass, "attribute", "patched")
            assert sample_module.SomeClass.attribute == "patched"

        def test_patch_attribute_unpatching_works(testslide):
            # This will fail if unpatching from test_mock_callable_patching_works does
            # not happen
            assert sample_module.SomeClass.attribute == "value"

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
    # asyncio-mode is not supported on python3.6
    if sys.version_info >= (3, 7):
        result = testdir.runpytest("-v", "--asyncio-mode=auto")
    else:
        result = testdir.runpytest("-v")
    assert "passed, 4 errors" in result.stdout.str()
    assert "failed" not in result.stdout.str()
    expected_failure = re.compile(
        r""".*_______ ERROR at teardown of test_mock_callable_failing_assertion_works ________
1 failures.
<class \'AssertionError\'>: calls did not match assertion.
\'time\', \'sleep\':
  expected: called exactly 1 time\(s\) with arguments:
    \(0,\)
  received: 0 call\(s\)
____ ERROR at teardown of test_mock_async_callable_failing_assertion_works _____
1 failures.
<class \'AssertionError\'>: calls did not match assertion.
<class \'tests.sample_module.ParentTarget\'>, \'async_static_method\':
  expected: called exactly 1 time\(s\) with arguments:
    \(\'a\', \'b\'\)
  received: 0 call\(s\)
______ ERROR at teardown of test_mock_constructor_failing_assertion_works ______
1 failures.
<class \'AssertionError\'>: calls did not match assertion.
<class \'testslide.mock_constructor.ParentTarget\'>, \'__new__\':
  expected: called exactly 1 time\(s\) with any arguments   received: 0 call\(s\)
_______________ ERROR at teardown of test_aggregated_exceptions ________________
2 failures.
<class \'AssertionError\'>: calls did not match assertion.
<StrictMock 0x[a-fA-F0-9]+ template=tests.sample_module.CallOrderTarget .*/test_pass0/test_pass.py:[0-9]+>, \'f1\':
  expected: called exactly 1 time\(s\) with arguments:
    \(\'a\',\)
  received: 0 call\(s\)
<class \'AssertionError\'>: calls did not match assertion.
<StrictMock 0x[a-fA-F0-9]+ template=tests.sample_module.CallOrderTarget .*/test_pass0/test_pass.py:[0-9]+>, \'f1\':
  expected: called exactly 1 time\(s\) with arguments:
    \(\'b\',\)
  received: 0 call\(s\).*""",
        re.MULTILINE | re.DOTALL,
    )
    assert expected_failure.match(result.stdout.str())
    assert result.ret != 0
