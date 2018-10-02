TestSlide's DSL
===============

When testing complex scenarios with lots of variations, or when doing `BDD <https://en.wikipedia.org/wiki/Behavior-driven_development>`_, TestSlide's DSL helps you break down your test cases close to spoken language. Composition of test scenarios enables covering more ground with less effort. Think of it as ``unittest.TestCase`` on steroids.

Quickstart
----------

Let's say we want to test this class:

.. code-block:: python

  import storage
  
  class Backup:
    def __init__(self):
      self.storage = storage.Client(timeout=60)
  
    def delete(self, path):
      self.storage.delete(path)

Here's a full example on how the DSL 

.. code-block:: python

  from testslide.dsl import context, fcontext, xcontext
  from testslide import StrictMock
  import storage
  import backup
  
  @context
  def Backup(context):
  
    context.memoize("backup", lambda self: backup.Backup())
  
    context.memoize("storage", lambda self: StrictMock(storage.Client))
  
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
      # Backup.delete
      @context.after
      def call_backup_delete(self):
        self.backup.delete(self.path)
  
      # Having all the context setup, we can now focus on the example,
      # that's gonna test that Backup.delete deletes the file on the
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


And when we run it:

.. code-block:: none

  $ testslide calc_test.py
  Backup
    delete
      it deletes from storage backend: PASS
  
  Finished 1 example(s) in 0.0s:
    Successful: 1

The key thing about the DSL, is that it allows composition, so you can arbitrarily nest contexts, that build on top of their parents.