mock_async_callable()
=====================

Just like :doc:`../mock_callable/index` works with regular callables, ``mock_async_callable()`` works with `coroutine functions <https://docs.python.org/3/glossary.html#term-coroutine-function>`_. It implements virtually the same interface (including with all its goodies), with only the following minor differences.

``.with_implementation()``
--------------------------

It requires an async function:

.. code-block:: python

  async def async_func():
    return 33
  
  self.mock_async_callable(some_object, 'some_method_name')\
    .with_implementation(async_func)
  await some_object.some_method_name()  # => 33

``.with_wrapper()``
-------------------

It requires an async function:

.. code-block:: python

  async def async_trim_query(original_async_callable):
    return await original_async_callable()[0:5]
  
  self.mock_async_callable(some_service, 'big_query')\
    .with_wrapper(async_trim_query)
  await some_service.big_query()  # => returns trimmed list

Test Framework Integration
--------------------------

Follows the exact same model as ``mock_callable()``, but it should be invoked as ``testslide.mock_callable.mock_async_callable``.