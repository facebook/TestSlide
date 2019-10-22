# TestSlide: Fluent Python Testing

[![Build Status](https://travis-ci.com/facebookincubator/TestSlide.svg?branch=master)](https://travis-ci.com/facebookincubator/TestSlide)
[![Documentation Status](https://readthedocs.org/projects/testslide/badge/?version=master)](https://testslide.readthedocs.io/en/master/?badge=master)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PyPI version](https://badge.fury.io/py/TestSlide.svg)](https://badge.fury.io/py/TestSlide)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

TestSlide makes writing tests fluid and easy. Whether you prefer classic [unit testing](https://docs.python.org/3/library/unittest.html), [TDD](https://en.wikipedia.org/wiki/Test-driven_development) or [BDD](https://en.wikipedia.org/wiki/Behavior-driven_development), it helps you be productive, with its easy to use well behaved mocks and its awesome test runner.

It is designed to work well with other test frameworks, so you can use it on top of existing `unittest.TestCase` without rewriting everything.

## Quickstart

Install:

```
pip install TestSlide
```

Scaffold the code you want to test `backup.py`:

```python
class Backup(object):
  def delete(self, path):
    pass
```

Write a test case `backup_test.py` describing the expected behavior:

```python
import testslide, backup, storage

class TestBackupDelete(testslide.TestCase):
  def setUp(self):
    super().setUp()
    self.storage_mock = testslide.StrictMock(storage.Client)
    # Makes storage.Client(timeout=60) return self.storage_mock
    self.mock_constructor(storage, 'Client')\
      .for_call(timeout=60)\
      .to_return_value(self.storage_mock)

  def test_delete_from_storage(self):
    # Set behavior and assertion for the call at the mock
    self.mock_callable(self.storage_mock, 'delete')\
      .for_call('/file/to/delete')\
      .to_return_value(True)\
      .and_assert_called_once()
    backup.Backup().delete('/file/to/delete')
```

TestSlide's `StrictMock`, `mock_constructor()` and `mock_callable()` are seamlessly integrated with Python's TestCase.

Run the test and see the failure:

![Failing test](https://raw.githubusercontent.com/facebookincubator/TestSlide/master/docs/test_fail.png)

TestSlide's mocks failure messages guide you towards the solution, that you can now implement:

```python
import storage

class Backup(object):
  def __init__(self):
    self.storage = storage.Client(timeout=60)

  def delete(self, path):
    self.storage.delete(path)
```

And watch the test go green:

![Passing test](https://raw.githubusercontent.com/facebookincubator/TestSlide/master/docs/test_pass.png)

It is all about letting the failure messages guide you towards the solution. There's a plethora of validation inside TestSlide's mocks, so you can trust they will help you iterate quickly when writing code and also cover you when breaking changes are introduced.

## Full documentation

There's a lot more that TestSlide can offer, please check the full documentation at https://testslide.readthedocs.io/ to learn more.

## Requirements

* Linux
* Python 3

## Join the TestSlide community

TestSlide is open source software, contributions are very welcome!

See the [CONTRIBUTING](CONTRIBUTING.md) file for how to help out.

## License

TestSlide is MIT licensed, as found in the [LICENSE](LICENSE) file.