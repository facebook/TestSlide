mock_constructor()
==================

Let's say we wan to unit test the ``Backup.delete`` method:

.. code-block:: python

  import storage
  
  class Backup(object):
    def __init__(self):
      self.storage = storage.Client(timeout=60)
  
    def delete(self, path):
      self.storage.delete(path)

We want to ensure that when ``Backup.delete`` is called, it actually deletes ``path`` from the storage as well, by calling ``storage.Client.delete``. We can leverage :doc:`../strict_mock/index` and :doc:`../mock_callable/index` for that:

.. code-block:: python

  self.storage_mock = StrictMock(storage.Client)
  self.mock_callable(self.storage_mock, 'delete')\
    .for_call('/file/to/delete')\
    .to_return_value(True)\
    .and_assert_called_once()
  Backup().delete('/file/to/delete')

The question now is: how to put ``self.storage_mock`` inside ``Backup.__init__``? This is where **mock_constructor** jumps in:

.. code-block:: python

  from testslide import TestCase, StrictMock, mock_callable
  import storage
  from backup import Backup
  
  class TestBackupDelete(TestCase):
    def setUp(self):
      super().setUp()
      self.storage_mock = StrictMock(storage.Client)
      self.mock_constructor(storage, 'Client')\
        .for_call(timeout=60)\
        .to_return_value(self.storage_mock)
  
    def test_delete_from_storage(self):
      self.mock_callable(self.storage_mock, 'delete')\
        .for_call('/file/to/delete')\
        .to_return_value(True)\
        .and_assert_called_once()
      Backup().delete('/file/to/delete')

mock_constructor makes ``storage.Client(timeout=60)`` return ``self.storage_mock``. It is similar to :doc:`../mock_callable/index`, accepting the same call, behavior and assertion definitions. Similarly, it will also fail if ``storage.Client()`` (missing timeout) is called.

Note how by using mock_constructor, not only you get all **safe by default** goodies, but also **totally decouples** your test from the code. This means that, no matter how ``Backup`` is refactored, the test remains the same.

Implementation Details
----------------------

In principle, doing:

.. code-block:: python

  self.mock_callable(SomeClass, '__new__')\
    .for_call()\
    .to_return_value(some_class_mock)

Should be all you need. However, as of October 2018, Python 3 has a bug https://bugs.python.org/issue25731 that prevents this from working (it works in Python 2).

mock_callable is a way to not only solve this for Python 3, but also provide the same interface for both.

Internally, mock_callable will:

* Patch the class at its module with a subclass of it, that is dynamically created.
* ``__new__`` of this dynamic subclass is handled by mock_callable.