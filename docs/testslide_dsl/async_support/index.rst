Async Support
=============

TestSlide's DSL supports `asynchronous I/O <https://docs.python.org/3/library/asyncio.html>`_ testing.

For that, you must declare all of these as async:

- Hooks: around, before and after.
- Examples.
- Memoize before.
- Functions.

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

    @context.function
    async def function(self):
      return "function"
  
    @context.example
    async def example(self):
      assert self.memoize_before == "memoize_before"
      assert self.function == "function"

The test runner will create a new event loop to execute each example.

.. note::

  You can **not** mix async and sync stuff for the same example. If your example is async, then all its hooks and memoize before must also be async.

.. note::

  It is not possible to support async ``@context.memoize``. They depend on `__getattr__ <https://docs.python.org/3/reference/datamodel.html#object.__getattr__>`_ to work, which has no async support. Use ``@context.memoize_before`` instead.


Event Loop Health
-----------------

`Event loops <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio-event-loop>`_ are the engine that runs Python async code. It works by alternating the execution between different bits of async code. Eg: when ``await`` is used, it allows the event loop to switch to another task. A requirement for this model to work is that async code must be "well behaved", so that it does what it needs to do without impacting other tasks.

TestSlide DSL has specific checks that detect if tested async code is doing something it should not.

Not Awaited Coroutine
^^^^^^^^^^^^^^^^^^^^^

Every called coroutine must be awaited. If they are not, it means their code never got to be executed, which indicates a bug in the code. In this example, a forgotten to be awaited coroutine triggers a test failure, despite the fact that no direct failure was reported by the test:

.. code-block:: python

  import asyncio
  from testslide.dsl import context

  @context
  def Not_awaited_coroutine(context):
    @context.example
    async def awaited_sleep(self):
      await asyncio.sleep(1)

    @context.example
    async def forgotten_sleep(self):
      asyncio.sleep(1)

.. code-block:: none

  $ testslide not_awaited_coroutine.py 
  Not awaited coroutine
    awaited sleep
    forgotten sleep: RuntimeWarning: coroutine 'sleep' was never awaited

  Failures:

    1) Not awaited coroutine: forgotten sleep
      1) RuntimeWarning: coroutine 'sleep' was never awaited
      Coroutine created at (most recent call last)
        File "/opt/python/lib/python3.7/site-packages/testslide/__init__.py", line 394, in run
          self._async_run_all_hooks_and_example(context_data)
        File "/opt/python/lib/python3.7/site-packages/testslide/__init__.py", line 334, in _async_run_all_hooks_and_example
          asyncio.run(coro, debug=True)
        File "/opt/python/lib/python3.7/asyncio/runners.py", line 43, in run
          return loop.run_until_complete(main)
        File "/opt/python/lib/python3.7/asyncio/base_events.py", line 566, in run_until_complete
          self.run_forever()
        File "/opt/python/lib/python3.7/asyncio/base_events.py", line 534, in run_forever
          self._run_once()
        File "/opt/python/lib/python3.7/asyncio/base_events.py", line 1763, in _run_once
          handle._run()
        File "/opt/python/lib/python3.7/asyncio/events.py", line 88, in _run
          self._context.run(self._callback, *self._args)
        File "/opt/python/lib/python3.7/site-packages/testslide/__init__.py", line 244, in _real_async_run_all_hooks_and_example
          self.example.code, context_data
        File "/opt/python/lib/python3.7/site-packages/testslide/__init__.py", line 218, in _fail_if_not_coroutine_function
          return await func(*args, **kwargs)
        File "/home/fornellas/tmp/not_awaited_coroutine.py", line 12, in forgotten_sleep
          asyncio.sleep(1)
        File "/opt/python/lib/python3.7/contextlib.py", line 119, in __exit__
          next(self.gen)

  Finished 2 example(s) in 1.0s
    Successful: 1
    Failed: 1

Slow Callback
^^^^^^^^^^^^^

Async code must do their work in small chunks, properly awaiting other functions when needed. If an async function does some CPU intensive task that takes a long time to compute, or if it calls a sync function that takes a long time to return, the entirety of the event loop will be locked up. This means that no other code can be executed until this bad async function returns.

If during the test execution a task blocks the event loop, it will trigger a test failure, despite the fact that no direct failure was reported by the test:

.. code-block:: python

  import time
  from testslide.dsl import context

  @context
  def Blocked_event_loop(context):
    @context.example
    async def blocking_sleep(self):
      time.sleep(1)

.. code-block:: none

  $ testslide blocked_event_loop.py 
  Blocked event loop
    blocking sleep: SlowCallback: Executing <Task finished coro=<_ExampleRunner._real_async_run_all_hooks_and_example() done, defined at /opt/python/lib/python3.7/site-packages/testslide/__init__.py:220> result=None created at /opt/python/lib/python3.7/asyncio/base_events.py:558> took 1.002 seconds

  Failures:

    1) Blocked event loop: blocking sleep
      1) SlowCallback: Executing <Task finished coro=<_ExampleRunner._real_async_run_all_hooks_and_example() done, defined at /opt/python/lib/python3.7/site-packages/testslide/__init__.py:220> result=None created at /opt/python/lib/python3.7/asyncio/base_events.py:558> took 1.002 seconds
        During the execution of the async test a slow callback that blocked the event loop was detected.
        Tip: you can customize the detection threshold with:
          asyncio.get_running_loop().slow_callback_duration = seconds
        File "/opt/python/lib/python3.7/contextlib.py", line 119, in __exit__
          next(self.gen)

  Finished 1 example(s) in 1.0s
    Failed: 1

Python's default threshold for triggering this event loop lock up failure is **100ms**. If your problem domain requires something smaller or bigger, you can easily customize it:

.. code-block:: python

  import asyncio
  import time
  from testslide.dsl import context

  @context
  def Custom_slow_callback_duration(context):
    @context.before
    async def increase_slow_callback_duration(self):
      loop = asyncio.get_running_loop()
      loop.slow_callback_duration = 2

    @context.example
    async def blocking_sleep(self):
      time.sleep(1)

.. code-block:: none

  $ testslide custom_slow_callback_duration.py 
  Custom slow callback duration
    blocking sleep

  Finished 1 example(s) in 1.0s
    Successful: 1

Leaked Tasks
^^^^^^^^^^^^

If your async code creates a task in the asyncio loop, but finished before that task has ended (ex. you forgot to await for it), testslide will catch it and fail the test.

This is enabled by default for async tests, but to get that behaviour also when running async code from sync tests, for example:


.. code-block:: python

  import asyncio
  from testslide.dsl import context

  @context
  def my_test_suite(context):
        @context.example
        def test_something_async(self):
            asyncio.run(my_async_function())


Has to use the `async_run_with_health_checks` function from the context, so instead, you should use:

.. code-block:: python

  import asyncio
  from testslide.dsl import context

  @context
  def my_test_suite(context):
        @context.example
        def test_something_async(self):
            self.async_run_with_health_checks(my_async_function())
