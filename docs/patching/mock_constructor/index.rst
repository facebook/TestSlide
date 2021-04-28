mock_constructor()
==================

Let's say we want to unit test the ``Backup.delete`` method:

.. code-block:: python

  import storage

  class Backup:
    def __init__(self):
      self.storage = storage.Client(timeout=60)

    def delete(self, path):
      self.storage.delete(path)

We want to ensure that when ``Backup.delete`` is called, it actually deletes ``path`` from the storage as well, by calling ``storage.Client.delete``. We can leverage :doc:`../../strict_mock/index` and :doc:`../mock_callable/index` for that:

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

``mock_constructor()`` makes ``storage.Client(timeout=60)`` return ``self.storage_mock``. It is similar to :doc:`../mock_callable/index`, accepting the same call, behavior and assertion definitions. Similarly, it will also fail if ``storage.Client()`` (missing timeout) is called.

Note how by using ``mock_constructor()``, not only you get all **safe by default** goodies, but also **totally decouples** your test from the code. This means that, no matter how ``Backup`` is refactored, the test remains the same.

.. note::

  Also check :doc:`../argument_matchers/index`: they allow more relaxed argument matching like "any string matching this regexp" or "any positive number".

Type Validation
---------------

``mock_constructor()`` uses type annotation information from constructors to validate that mocks are respecting the interface:

.. code-block:: python

  import sys
  import testslide, testslide.lib

  class Messenger:
      def __init__(self, message: str):
        self.message = message

  class TestArgumentTypeValidation(testslide.TestCase):
      def test_argument_type_validation(self):
          messenger_mock = testslide.StrictMock(template=Messenger)
          self.mock_constructor(sys.modules[__name__], "Messenger").to_return_value(messenger_mock)
          with self.assertRaises(testslide.lib.TypeCheckError):
              # TypeCheckError: Call with incompatible argument types:
              # 'message': type of message must be str; got int instead
              Messenger(message=1)

If you need to disable it (potentially due to a bug, please report!) you can do so with: ``mock_constructor(module, class_name, type_validation=False)``.

Caveats
-------

Because of the way ``mock_constructor()`` must be implemented (see next section), its usage must respect these rules:

- References to the mocked class saved prior to ``mock_constructor()`` invocation **can not be used**, including previously created instances.
- Access to the class must happen exclusively via attribute access (eg: ``getattr(some_module, "SomeClass")``).

A simple easy way to ensure this is to always:

.. code-block:: python

  # Do this:
  import some_module
  some_module.SomeClass
  # Never do:
  from some_module import SomeClass

.. note::

  Not respecting these rules will break ``mock_constructor()`` and can lead to unpredicted behavior!

Implementation Details
^^^^^^^^^^^^^^^^^^^^^^

``mock_callable()`` should be all you need:

.. code-block:: python

  self.mock_callable(SomeClass, '__new__')\
    .for_call()\
    .to_return_value(some_class_mock)

However, as of July 2019, Python 3 has an open bug https://bugs.python.org/issue25731 that prevents ``__new__`` from being patched. ``mock_constructor()`` is a way around this bug.

Because ``__new__`` can not be patched, we need to handle things elsewhere. The trick is to dynamically create a subclass of the target class, make the changes to ``__new__`` there (so we don't touch ``__new__`` at the target class), and patch it at the module in place of the original class.

This works when ``__new__`` simply returns a mocked value, but creates issues when used with ``.with_wrapper()`` or ``.to_call_original()`` as both requires calling the original ``__new__``. This will return an instance of the original class, but the new subclass is already patched at the module, thus ``super()`` / ``super(Class, self)`` breaks. If we make them call ``__new__`` from the subclass, the call comes from... ``__new__`` and we get an infinite loop. Also, ``__new__`` calls ``__init__`` unconditionally, not allowing ``.with_wrapper()`` to mangle with the arguments.

The way around this, is to keep the original class where it is and move all its attributes to the child class:

* Dynamically create the subclass of the target class, with the same name.
* Move all ``__dict__`` values from the target class to the subclass (with a few exceptions, such as ``__new__`` and ``__module__``).
* At the subclass, add a ``__new__`` that works as a factory, that allows ``mock_callable()`` interface to work.
* Do some trickery to fix the arguments passed to ``__init__`` to allow ``.with_wrapper()`` mangle with them.
* Patch the subclass in place of the original target class at its module.
* Undo all of this when the test finishes.

This essentially creates a "copy" of the class, at the subclass, but with ``__new__`` implementing the behavior required. All things such as class attributes/methods and ``isinstance()`` are not affected. The only noticeable difference, is that ``mro()`` will show the extra subclass.

Test Framework Integration
--------------------------

TestSlide's DSL
^^^^^^^^^^^^^^^

Integration comes out of the box for :doc:`../../testslide_dsl/index`: you can simply do ``self.mock_constructor()`` from inside examples or hooks.

Python Unittest
^^^^^^^^^^^^^^^

``testslide.TestCase`` is provided with off the shelf integration ready:

- Inherit your ``unittest.TestCase`` from it.
- If you overload ``unittest.TestCase.setUp``, make **sure** to call ``super().setUp()`` before using ``mock_constructor()``.

Any Test Framework
^^^^^^^^^^^^^^^^^^

You must follow these steps for **each** test executed that uses ``mock_constructor()``:

* Integrate :doc:`../mock_callable/index` (used by mock_constructor under the hood).
* After each test execution, you must **unconditionally** call ``testslide.mock_constructor.unpatch_all_callable_mocks``. This will undo all patches, so the next test is not affected by them. Eg: for Python's unittest: ``self.addCleanup(testslide.mock_constructor.unpatch_all_callable_mocks)``.
* You can then call ``testslide.mock_constructor.mock_constructor`` directly from your tests.
