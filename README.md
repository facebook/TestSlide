# TestSlide: Fluent Python Testing

[![Build Status](https://api.travis-ci.org/facebookincubator/TestSlide.svg?branch=master)](https://travis-ci.org/facebookincubator/TestSlide)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PyPI version](https://badge.fury.io/py/TestSlide.svg)](https://badge.fury.io/py/TestSlide)

TestSlide makes writing tests fluid and easy. It allows complex mock setup without manual labor. TestSlide's mocks have a plethora of validations under the hood, so you can trust your test signal, specially when code changes. [TDD](https://en.wikipedia.org/wiki/Test-driven_development) and [BDD](https://en.wikipedia.org/wiki/Behavior-driven_development) are well supported by a [DSL](https://en.wikipedia.org/wiki/Domain-specific_language), that allows you to describe your test cases close to spoken language. The included test runner, is full of nice features, allowing you to iterate quickly.

Getting started takes only a few minutes. You can even use its components with existing `unittest.TestCase` (or any other test framework), without rewriting everything.

## Examples

Here are a few examples of TestSlide's components. Don't forget to refer to the full documentation at https://testslide.readthedocs.io/.

- [Test Runner](#test-runner)
- [StrictMock](#strictmock)
- [mock_callable()](#mock_callable)
- [mock_constructor()](#mock_constructor)
- [TestSlide's DSL](#testslides-dsl)

### Test Runner

TesSlide's Test Runner can execute pre-existing `unittest.TestCase` tests. Let's say we have these tests for a calculator:

```python
# calc_test.py
class TestCalcAdd(unittest.TestCase):
  def test_add_positive(self):
    self.assertEqual(Calc().add(1, 2), 3)

  def test_add_negative(self):
    self.assertEqual(Calc().add(-1, -2), -3)

class TestCalcSub(unittest.TestCase):
  def test_sub_positive(self):
    self.assertEqual(Calc().sub(1, 2), -1)

  def test_sub_negative(self):
    self.assertEqual(Calc().sub(-1, -2), 1)
```

You can execute it with:

```
$ testslide calc_test.py
calc_test.TestCalcAdd
  test_add_negative: PASS
  test_add_positive: PASS
calc_test.TestCalcSub
  test_sub_negative: PASS
  test_sub_positive: PASS

Finished 4 example(s) in 0.0s:
  Successful:  4
```

Note how the logical organization of the tests are kept. If failure happens, it is also very friently:

```
$ testslide --fail-fast calc_test.py
calc_test.TestCalcAdd
  test_add_negative: AssertionError: -2 != -3

Failures:

  1) calc_test.TestCalcAdd: test_add_negative
    1) AssertionError: -2 != -3
      File "calc_test.py", line 9, in test_add_negative
        self.assertEqual(Calc().add(-1, -2), -3)
      File "/opt/python3/lib/python3.6/unittest/case.py", line 829, in assertEqual
        assertion_func(first, second, msg=msg)
      File "/opt/python3/lib/python3.6/unittest/case.py", line 822, in _baseAssertEqual
        raise self.failureException(msg)

Finished 1 example(s) in 0.0s:
  Failed:  1
  Not executed:  3
```

One cool feature, is that you can focus execution for a single test **from within your text editor** just by changing `def test` to `def ftest`:

```python
  def ftest_sub_positive(self):
    self.assertEqual(Calc().sub(1, 2), -1)
```

And then run only this test:

```
$ testslide --fail-fast --focus calc_test.py
calc_test.TestCalcAdd
  *ftest_add_negative: AssertionError: -2 != -3

Failures:

  1) calc_test.TestCalcAdd: ftest_add_negative
    1) AssertionError: -2 != -3
      File "calc_test.py", line 9, in ftest_add_negative
        self.assertEqual(Calc().add(-1, -2), -3)
      File "/opt/python3/lib/python3.6/unittest/case.py", line 829, in assertEqual
        assertion_func(first, second, msg=msg)
      File "/opt/python3/lib/python3.6/unittest/case.py", line 822, in _baseAssertEqual
        raise self.failureException(msg)

Finished 1 example(s) in 0.0s:
  Failed:  1
  Not executed:  3

```

You can similarly skip a test with `def xtest`.

### `StrictMock`

`StrictMock` is a mock object that is **safe by default**. To understand what that means, let's see how the usual Mock behaves:

```python
from urllib.request import Request
from unittest.mock import Mock
mock = Mock(Request)
if mock.has_proxy():
  print('Always runs!')
```

It returns another `Mock` for every attribute by default. And it is always `True`. This might not be what you need, meaning you can **not trust your test signal**. Also, it accepts whatever arguments you throw at it:

```python
mock.has_proxy('whatever', 'junk', 'you', 'send', 'is', 'ok')
```

`StrictMock` addresses this, by not trying to guess what it should do:

```python
from urllib.request import Request
from testslide import StrictMock
mock = StrictMock(Request)
mock.has_proxy()  # => raises UndefinedBehavior
```

You can then, easily add the behavior you need for your test case:

```python
mock.has_proxy = lambda : False
mock.has_proxy()  # => False
```

`StrictMock` also covers you, in case you try to do something clowny:

```python
mock.has_proxy = lambda invalid_arg: False
mock.has_proxy('invalid')  # => raises TypeError
```

All this means you can have much more reliable test signal, even when code changes.

### `mock_callable()`

`mock_callable()` helps you define behavior for instance/static/class methods, for **either mocks or real objects**. You tell what calls to accept, with what arguments and what to do when the call is made. Optionally, you can define assertions on the number of calls. It is also **safe by default**, rejecting unconfigured calls. Let's see an example:

```python
from urllib.request import Request
from testslide import TestCase, StrictMock

class TestRequest(TestCase):
  def setUp(self):
    self.request = StrictMock(Request)
    self.mock_callable(self.request, 'get_header')\
      .for_call('Host')\
      .to_return_value('example.com')
      .and_assert_called_once()

  def test_call_once(self):
    'Passes because call was made once'
    self.assertEqual(
      self.request.get_header('Host'),
      'example.com',
    )

  def test_no_call(self):
    'Fails because no call was made'
    pass

  def test_calls_twice(self):
    'Fails because multiple calls were made'
    self.request.get_header('Host')
    self.request.get_header('Host')

  def test_call_unexpected_args(self):
    'Fails because no behavior was defined for this argument'
    self.request.get_header('Accept')  # => raises UndefinedBehaviorForCall

  def test_compose_behavior(self):
    'Passes as new behavior was added on top of the previous'
    self.mock_callable(self.request, 'get_header')\
      .for_call('Accept')\
      .to_return_value('*/*')
    self.assertEqual(
      self.request.get_header('Host'),
      'example.com',
    )
    self.assertEqual(
      self.request.get_header('Accept'),
      '*/*',
    )
```

`mock_callable()` is flexible, allowing complex behavior to be defined quickly.

Here's a list of all behaviors you can define:

```python
to_return_value(value)
to_return_values(values_list)
to_yield_values(values_list)
to_raise(exception)
with_implementation(func)
with_wrapper(func)
to_call_original()
```

And all (optional) assertions:

```python
and_assert_called_exactly(times)
and_assert_called_once()
and_assert_called_twice()
and_assert_called_at_least(times)
and_assert_called_at_most(times)
and_assert_called()
and_assert_not_called()
```

### `mock_constructor()`

`mock_constructor()` is `StrictMock`'s companion, allowing you to take control of instance creation, so you can put your mocks in place. Let's see it in action.

Let's say we have this backup client class, that depends on some storage backend:

```python
import storage

class BackupClient:
  def __init__(self):
    self.storage = storage.Client(timeout=60)

  def delete(self, path):
    self.storage.delete(path)
```

When testing the delete method, we want to ensure that it called delete on the storage backend:

```python
from testslide import TestCase, StrictMock
import storage

class TestBackup(TestCase):
  def setUp(self):
    self.storage = StrictMock(storage.Client)
    self.mock_constructor(storage, 'Client')\
      .for_call(timeout=60)\
      .to_return_value(self.storage)

  def test_delete(self):
    self.mock_callable(self.storage, 'delete')\
      .for_call('/some/file')\
      .to_return_value(True)\
      .and_assert_called_once()
    Backup().delete('/some/file')
```

* `mock_constructor()` patches `storage.Client` constructor to when called with `timeout=60` to return the mock.
* We then use `mock_callable()` to define the precise call assertion on `storage.Client.delete`.

`mock_constructor()`'s interface is similar to `mock_callable()`, accepting the same behavior definitions. It is also **safe by default**, rejecting any unexpected constructor calls.

The big win is the decoupling from test to implementation, which makes refactoring a breeze.

### TestSlide's DSL

To aid [BDD](https://en.wikipedia.org/wiki/Behavior-driven_development), TestSlide provides a [DSL](https://en.wikipedia.org/wiki/Domain-specific_language) that allows you to break down your test cases close to spoken language.

The following example, shows how to test the `BackupClient` form the previous section:

```python
from testslide.dsl import context
from testslide import StrictMock
import storage
import backup

# We declare a context for what we want to test
@context
def BackupClient(context):

  # Inside the context, we say it'll have an attribute "backup", our target.
  # Note it is declared as a lambda, so it will be evaluated for each example.
  context.memoize("backup", lambda self: backup.BackupClient())

  # This is the mock for the storage backend, that we will need to patch at
  # storage.Client's constructor (below)
  context.memoize("storage", lambda self: StrictMock(storage.Client))

  # Before executing each example, storage.Client constructor will be mocked
  # to return its mock instead.
  @context.before
  def mock_storage_Client(self):
    # With this, Client's constructor will return the mock, *only* when
    # called with timeout=60. If any other call is received, the test
    # will fail.
    self.mock_constructor(storage, 'Client')\
      .for_call(timeout=60)\
      .to_return_value(self.storage)

  # We now nest another context, specifying we are testing the delete method.
  @context.sub_context
  def delete(context):
    context.memoize("path", lambda self: '/some/file')

    # After every example within this context, we want to call
    # BackupClient.delete
    @context.after
    def call_backup_delete(self):
      self.backup.delete(self.path)

    # Having all the context setup, we can now focus on the example,
    # that's gonna test that BackupClient.delete deletes the file on the
    # storage backend.
    @context.example
    def it_deletes_from_storage_backend(self):
      # This mocks the storage backend to accept the delete call, and
      # also creates an assertion that it must have happened exactly
      # once. The test will fail if the call does not happen, happens
      # more than once or happens with different arguments.
      self.mock_callable(self.storage, 'delete')\
        .for_call(self.path)\
        .to_return_value(True)\
        .and_assert_called_once()
```

And when we run it:

```
$ testslide calc_test.py
BackupClient
  delete
    it deletes from storage backend: PASS

Finished 1 example(s) in 0.0s:
  Successful: 1
```

The key thing about the DSL, is that it allows composition, so you can arbitrarily nest contexts, that build on top of their parents.

## Requirements

TestSlide is thoroughly tested to work with:

* Linux
* Python 2 / 3

## Building TestSlide

TestSlide is packaged using [setuptools](https://pypi.org/project/setuptools/), so you can build it following its docs. This [doc](https://packaging.python.org/guides/distributing-packages-using-setuptools/) on Python packaging can also be useful.

## Installing TestSlide

You can install it with pip:

```
pip install TestSlide
```

Please refer to [this documentation](https://packaging.python.org/discussions/install-requires-vs-requirements/#install-requires-vs-requirements-files) on how to integrate TestSlide as a dependency in your project.

## How TestSlide works

TestSlide has several independent components, that you can use altogether, or cherry pick the ones you like, and use with your favorit test framework.

## Full documentation

https://testslide.readthedocs.io/

## Join the TestSlide community

* Website: https://github.com/facebookincubator/TestSlide
See the [CONTRIBUTING](CONTRIBUTING.md)  file for how to help out.

## License
TestSlide is MIT licensed, as found in the [LICENSE](LICENSE) file.