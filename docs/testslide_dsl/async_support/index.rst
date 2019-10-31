Async Support
=============

TestSlide's DSL supports `asynchronous I/O <https://docs.python.org/3/library/asyncio.html>`_ testing.

For that, you must declare all of these as async:

- Hooks: around, before and after.
- Examples.
- Memoize before.

like this:

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
  
    @context.memoize_before
    async def memoize_before(self):
      return "memoize_before"
  
    @context.example
    async def example(self):
      assert self.memoize_before == "memoize_before"

The test runner will create a new event look to execute each example.

.. note::

  You can **not** mix async and sync stuff for the same example. If your example is async, then all its hooks and memoize before must also be async.

.. note::

  It is not possible to support async ``@context.memoize``. They depend on `__getattr__ <https://docs.python.org/3/reference/datamodel.html#object.__getattr__>`_ to work, which has no async support. Use ``@context.memoize_before`` instead.