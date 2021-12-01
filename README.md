![TestSlide](./docs/testslide_logo.png)

[![Build Status](https://github.com/facebook/TestSlide/workflows/CI/badge.svg)](https://github.com/facebook/TestSlide/actions?query=workflow%3ACI)
[![Coverage Status](https://coveralls.io/repos/github/facebook/TestSlide/badge.svg?branch=main)](https://coveralls.io/github/facebook/TestSlide?branch=main)
[![Documentation Status](https://readthedocs.org/projects/testslide/badge/?version=main)](https://testslide.readthedocs.io/en/main/?badge=main)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PyPI version](https://badge.fury.io/py/TestSlide.svg)](https://badge.fury.io/py/TestSlide)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

A test framework for Python that enable [unit testing](https://docs.python.org/3/library/unittest.html) / [TDD](https://en.wikipedia.org/wiki/Test-driven_development) / [BDD](https://en.wikipedia.org/wiki/Behavior-driven_development) to be productive and enjoyable.

Its well behaved mocks with thorough API validations catches bugs both when code is first written or long in the future when it is changed.

The flexibility of using them with existing `unittest.TestCase` or TestSlide's own test runner let users get its benefits without requiring refactoring existing code.

## Quickstart

Install:

```
pip install TestSlide
```

Scaffold the code you want to test `backup.py`:

```python
class Backup:
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

![Failing test](https://raw.githubusercontent.com/facebook/TestSlide/main/docs/test_fail.png)

TestSlide's mocks failure messages guide you towards the solution, that you can now implement:

```python
import storage

class Backup:
  def __init__(self):
    self.storage = storage.Client(timeout=60)

  def delete(self, path):
    self.storage.delete(path)
```

And watch the test go green:

![Passing test](https://raw.githubusercontent.com/facebook/TestSlide/main/docs/test_pass.png)

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


## Terms of Use

https://opensource.facebook.com/legal/terms


## Privacy Policy

https://opensource.facebook.com/legal/privacy

## Copyright

Copyright © 2021 Meta Platforms, Inc
