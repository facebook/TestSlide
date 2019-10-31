Async Support
=============

TestSlide's DSL supports `asynchronous I/O <https://docs.python.org/3/library/asyncio.html>`_ testing. For that you must:

- Declare contexts as sync functions as usual.
- Declare examples and hooks (around, before and after) as async.

Example:

.. code-block:: python

  from testslide.dsl import context
  
  @context
  def testing_async_code(context):
    @context.around
    async def around(self, example):
      await example()  # Note that this must be awaited!

    @context.before
    async def before(self):
      pass

    @context.after
    async def after(self):
      pass

    @context.example
    async def example(self):
      pass

The test runner will create a new event look to execute each example with all its hooks.

.. note::

  You can **not** mix async and sync examples and functions. If your example is sync, all its hooks must be sync; if the example is async, all its hooks must be async.