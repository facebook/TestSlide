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

``mock_callable()`` should be all you need:

.. code-block:: python

  self.mock_callable(SomeClass, '__new__')\
    .for_call()\
    .to_return_value(some_class_mock)

However, as of July 2019, Python 3 has an open bug https://bugs.python.org/issue25731 that prevents this from working. ``mock_constructor`` is a way around this bug.

Because ``__new__`` can not be patched, we need to handle things elsewhere:

* Dynamically create a subclass of the target class, with the same name.
* Move all ``__dict__`` values from the target class to the subclass (with a few exceptions).
* In the subclass, add a ``__new__`` that works as a factory, that allows ``mock_callable()`` to work.
* Do some trickery to fix the arguments passed to ``__init__`` to allow ``.with_wrapper()`` mangle with them (as by default,``__new__`` unconditionally calls ``__init__`` with the same arguments received).
* Patch the subclass in place of the original target class at its module.
* Undo all of this when the test finishes.

As this effectively only changes the behavior of ``__new__``, things like class attributes, class methods and ``isinstance()`` are not affected. The only noticeable difference, is that ``mro()`` will show the extra subclass.

Integration With Other Frameworks
---------------------------------

mock_constructor comes out of the box with support for Python`s unittest (via ``testslide.TestCase``) and :doc:`../testslide_dsl/index`. You can easily integrate it with any other test framework you prefer:

* Integrate :doc:`../mock_callable/index` (used by mock_constructor under the hook).
* After each test execution, you must **unconditionally** call ``testslide.mock_constructor.unpatch_all_callable_mocks``. This will undo all patches, so the next test is not affected by them. Eg: for Python's unittest: ``self.addCleanup(testslide.mock_constructor.unpatch_all_callable_mocks)``.
* You can then call ``testslide.mock_constructor.mock_constructor`` directly from your tests.