TestSlide: Fluent Python Testing
================================

TestSlide makes writing tests fluid and easy. Whether you prefer classic `unit testing <https://docs.python.org/3/library/unittest.html>`_, `TDD <https://en.wikipedia.org/wiki/Test-driven_development>`_ or `BDD <https://en.wikipedia.org/wiki/Behavior-driven_development>`_, it  helps you be productive, with its easy to use well behaved mocks and its awesome test runner.

TestSlide is designed to work well with other test frameworks, so you can use it on top of existing ``unittest.TestCase`` without rewriting everything.

Quickstart
----------

Install the package:

.. code-block:: none

  pip install TestSlide

Scaffold the code you want to test ``backup.py``:

.. code-block:: python

  class BackupClient:
    def delete(self, path):
      pass

Write a test case for it ``backup_test.py``:

.. code-block:: python

  from testslide import TestCase, StrictMock, mock_callable
  import storage
  from backup import Backup
  
  class TestBackupDelete(TestCase):
    def setUp(self):
      super().setUp()
      self.storage = StrictMock(storage.Client)
      self.mock_constructor(storage, 'Client')\
        .for_call(timeout=60)\
        .to_return_value(self.storage)
    
    def test_delete_from_storage(self):
      self.mock_callable(self.storage, 'delete')\
        .for_call('/file/to/delete')\
        .to_return_value(True)\
        .and_assert_called_once()
      Backup().delete('/file/to/delete')

.. note::

  TestSlide's :doc:`strict_mock/index` , :doc:`mock_callable/index` and :doc:`mock_constructor/index` are used seamlessly with Python's unittest. You can also use :doc:`testslide_dsl/index` to write tests.

Run the test and see the failure:

.. image:: test_fail.png
   :alt: Test failure
   :align: center

TestSlide's mocks failure messages guide you towards the solution, that you can now implement:

.. code-block:: python

  class Backup:
    def __init__(self):
      self.storage = storage.Client(timeout=60)
  
    def delete(self, path):
      self.storage.delete(path)

And watch the test go green:

.. image:: test_pass.png
   :alt: Test pass
   :align: center

It is all about letting the failure messages guide you towards the solution. There's a plethora of validation inside TestSlide's mocks, so you can trust they will help you iterate quickly when writing code and also cover you when breaking changes are introduced.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   test_runner/index.rst
   strict_mock/index.rst
   mock_callable/index.rst
   mock_constructor/index.rst
   testslide_dsl/index.rst
   writing_good_tests/index.rst