TestSlide's DSL
===============

When testing complex scenarios with lots of variations, or when doing `BDD <https://en.wikipedia.org/wiki/Behavior-driven_development>`_, TestSlide's DSL helps you break down your test cases close to spoken language. Composition of test scenarios enables covering more ground with less effort. Think of it as ``unittest.TestCase`` on steroids.

Let's say we want to test this class:

.. code-block:: python

  import storage
  
  class Backup:
    def __init__(self):
      self.storage = storage.Client(timeout=60)
  
    def delete(self, path):
      self.storage.delete(path)

We can test it with:

.. code-block:: python

  from testslide.dsl import context
  from testslide import StrictMock
  import storage
  import backup
  
  @context
  def Backup(context):
  
    context.memoize("backup", lambda self: backup.Backup())
  
    context.memoize("storage_mock", lambda self: StrictMock(storage.Client))
  
    @context.before
    def mock_storage_Client(self):
      self.mock_constructor(storage, 'Client')\
        .for_call(timeout=60)\
        .to_return_value(self.storage_mock)
  
    @context.sub_context
    def delete(context):
      context.memoize("path", lambda self: '/some/file')
  
      @context.after
      def call_backup_delete(self):
        self.backup.delete(self.path)
  
      @context.example
      def it_deletes_from_storage_backend(self):
        self.mock_callable(self.storage_mock, 'delete')\
          .for_call(self.path)\
          .to_return_value(True)\
          .and_assert_called_once()

And when we run it:

.. code-block:: none

  $ testslide backup_test.py
  Backup
    delete
      it deletes from storage backend
  
  Finished 1 example(s) in 0.0s:
    Successful: 1

As you can see, we can declare contexts for testing, and keep building on top of them:

* The top ``Backup`` context contains the object we want to test, and the common mocks needed.
* The nested ``delete`` context always calls ``Backup.delete`` after each example.
* The ``it_deletes_from_storage_backend`` example defines only the assertion needed for it.

As the ``Backup`` class grows, it is easy to nest new contexts, and reuse what's already defined.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   contexts_and_examples/index.rst
   shared_contexts/index.rst
   context_hooks/index.rst
   context_attributes_and_functions/index.rst
   skip_and_focus/index.rst
   unittest_testcase_integration/index.rst
   async_support/index.rst