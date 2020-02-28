StrictMock
==========

Often code we write depends on external things such as a database or a REST API. We can test our code allowing it to talk directly to those dependencies, but there are different reasons why we wouldn't want to:

- The dependency is available as a production environment only and we can't let a test risk breaking production.
- The dependency is not available on all environments the test is being executed, for example during a Continuous Integration build.
- We want to test different scenarios, such as a valid response, error response or a timeout.

**Mocks** helps us achieve this goal when used in place of a real dependency. They need to respond conforming to the same interface exposed by the dependency, allowing us to configure canned responses to simulate the different scenarios we need. This must be true if we want to trust our test results.

Yet Another Mock?
-----------------

`Python unittest <https://docs.python.org/3/library/unittest.html>`_ already provides us with ``Mock``, ``PropertyMock``, ``AsyncMock``, ``MagicMock``, ``NonCallableMagicMock``... each for a specific use case. To understand what ``StrictMock`` brings to the table, let's start by looking at Python's mocks.

Let's pretend we depend on a ``Calculator`` class and we want to create a mock for it:

.. code-block:: ipython

  In [1]: from unittest.mock import Mock

  In [2]: class Calculator:
     ...:   def is_odd(self, x):
     ...:     return bool(x % 2)
     ...:

  In [3]: mock = Mock(Calculator)

  In [4]: mock.is_odd(2)
  Out[4]: <Mock name='mock.is_odd()' id='140674180253512'>

  In [5]: bool(mock.is_odd(2))
  Out[5]: True

  In [6]: mock.is_odd(2, 'invalid')
  Out[6]: <Mock name='mock.is_odd()' id='140674180253512'>


Wow! The calculator mock is lying to us telling that 2 is odd! And worse: we are able to violate the method signature without issues! How can we trust our tests with mocks like this? **This is precisely the kind of problem** ``StrictMock`` **solves!**

.. note::

  Since Python 3.7 we can `seal <https://docs.python.org/3/library/unittest.mock.html#unittest.mock.seal>`_ mocks. This helps, but as you will see, ``StrictMock`` has a lot unpaired functionality.

A Mock You Can Trust
--------------------

``StrictMock`` allows you to create **mocks of instances of a given template class**. Its default is **not** to give arbitrary canned responses, but rather be clear that it is missing some configuration:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class Calculator:
     ...:     def is_odd(self, x):
     ...:         return bool(x % 2)
     ...:

  In [3]: mock = StrictMock(template=Calculator)

  In [4]: mock.is_odd(2)
  (...)
  UndefinedAttribute: 'is_odd' is not defined.
  <StrictMock 0x7F17E06C7310 template=__main__.Calculator> must have a value defined for this attribute if it is going to be accessed.

So, let's define ``is_odd`` method:

.. code-block:: ipython

  In [5]: mock.is_odd = lambda number: False

  In [6]: mock.is_odd(2)
  Out[6]: False

As we saw, ``StrictMock`` is **safe by default**: any attribute access will raise ``UndefinedAttribute`` unless it had a value set previously. As you are in control of what values you assign to your mock, you can trust it to do only what you expect it to do.

Under the hood there's tons of validation to ensure the mock's interface precisely matches the template class.

.. note::

  - Refer to :doc:`../patching/mock_callable/index` to learn to tighten what arguments ``is_odd()`` should accept.
  - Refer to :doc:`../patching/mock_constructor/index` to learn how to put ``StrictMock`` in place of your dependency.

Configuration
-------------

Constructor
^^^^^^^^^^^

Naming
""""""

You can optionally name your mock, to make it easier to identify:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: str(StrictMock())
  Out[2]: '<StrictMock 0x7F7A30FC0748>'

  In [3]: str(StrictMock(name='whatever'))
  Out[3]: "<StrictMock 0x7F7A30FDFF60 name='whatever'>"

Generic Mocks
"""""""""""""

It is higly recommended to use ``StrictMock`` giving it a template class, so you can leverage its interface validation. There are situations however that any "generic mock" is good enough. You can still use StrictMock, although you'll loose most validations:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: mock = StrictMock()

  In [3]: mock.whatever
  (...)
  UndefinedAttribute: 'whatever' is not defined.
  <StrictMock 0x7FED1C724C18> must have a value defined for this attribute if it is going to be accessed.

  In [4]: mock.whatever = 'something'

  In [5]: mock.whatever
  Out[5]: 'something'

It will accept setting any attributes, with any values.

Template Class
""""""""""""""

By giving a template class, we can leverage all interface validation goodies:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class Calculator:
     ...:     def is_odd(self, x):
     ...:         return bool(x % 2)
     ...:

  In [3]: mock = StrictMock(template=Calculator)

  In [4]: mock.is_odd(2)
  (...)
  UndefinedAttribute: 'is_odd' is not defined.
  <StrictMock 0x7F17E06C7310 template=__main__.Calculator> must have a value defined for this attribute if it is going to be accessed.

Runtime Attributes
""""""""""""""""""

``StrictMock`` introspects the template's ``__init__`` code to find attributes that are dynamically set during runtime. If this mechanism fails (often a source of bad class design), you should inform ``StrictMock`` about those attributes:

.. code-block:: python

  StrictMock(template=TemplateClass, runtime_attrs=['attr_set_at_runtime'])

Default Context Manager
"""""""""""""""""""""""

If the template class is a context manager, ``default_context_manager`` can be used to automatically setup ``__enter__`` and ``__exit__`` mocks for you:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class CM:
     ...:   def __enter__(self):
     ...:     return self
     ...:
     ...:   def __exit__(self, exc_type, exc_value, traceback):
     ...:     pass
     ...:

  In [3]: mock = StrictMock(template=CM, default_context_manager=True)

  In [4]: with mock as m:
     ...:   assert id(mock) == id(m)
     ...:

The mock itself is yielded.

.. note::

  This also works for `asynchronous context managers <https://docs.python.org/3/reference/datamodel.html#asynchronous-context-managers>`_.

Disabling Signature Validation
""""""""""""""""""""""""""""""
By default, ``StrictMock`` will validate arguments passed to callable attributes - it does this by inserting a proxy object in between the attribute and the value. In some rare situations, this proxy object can cause issues (eg if you ``assert type(self.attr) == Foo``). If having ``type()`` return the correct value is more important than having signatures validated, you can disable signature validation:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class CallableObject(object):
     ...:   def __call__(self):
     ...:     pass
     ...:

  In [3]: s = StrictMock()

  In [4]: s.attr = CallableObject()

  In [5]: type(s.attr)
  Out[5]: testslide.strict_mock._MethodProxy

  In [6]: s = StrictMock(signature_validation=False)

  In [7]: s.attr = CallableObject()

  In [8]: type(s.attr)
  Out[8]: __main__.CallableObject

Setting Attributes
^^^^^^^^^^^^^^^^^^

Regular
"""""""

They can be set as usual:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: mock = StrictMock()

  In [3]: mock.whatever
  (...)
  UndefinedAttribute: 'whatever' is not defined.
  <StrictMock 0x7FED1C724C18> must have a value defined for this attribute if it is going to be accessed.

  In [4]: mock.whatever = 'something'

  In [5]: mock.whatever
  Out[5]: 'something'

Other than if the attribute is allowed to be set (based on the optional template class), no validation is performed on the value assigned.

Methods
"""""""

You can assign callables to instance, class and static methods as usual. There's special mechanics under the hood to ensure the mock will receive the correct arguments:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
     ...:

  In [2]: class Echo:
     ...:   def instance_echo(self, message):
     ...:     return message
     ...:
     ...:   @classmethod
     ...:   def class_echo(cls, message):
     ...:     return message
     ...:
     ...:   @staticmethod
     ...:   def static_echo(message):
     ...:     return message
     ...:

  In [3]: mock = StrictMock(template=Echo)
     ...:

  In [4]: mock.instance_echo = lambda message: f"mock: {message}"
     ...:

  In [5]: mock.instance_echo("hello")
     ...:
  Out[5]: 'mock: hello'

  In [6]: mock.class_echo = lambda message: f"mock: {message}"
     ...:

  In [7]: mock.class_echo("hello")
     ...:
  Out[7]: 'mock: hello'

  In [8]: mock.static_echo = lambda message: f"mock: {message}"
     ...:

  In [9]: mock.static_echo("hello")
     ...:
  Out[9]: 'mock: hello'

You can also use regular methods:

.. code-block:: ipython

  In [11]: def new(message):
      ...:     return f"new {message}"
      ...:

  In [12]: mock.instance_echo = new

  In [13]: mock.instance_echo("Hi")
  Out[13]: 'new Hi'

Or even methods from any instances:

.. code-block:: ipython

  In [14]: class MockEcho:
      ...:     def echo(self, message):
      ...:         return f"MockEcho {message}"
      ...:

  In [15]: mock.class_echo = MockEcho().echo

  In [16]: mock.class_echo("Wow!")
  Out[16]: 'MockEcho Wow!'

Magic Methods
^^^^^^^^^^^^^

Magic Methods must be defined at the instance's class and not the instance. ``StrictMock`` has special mechanics that allow you to set them **per instance** trivially:

 .. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: mock = StrictMock()

  In [3]: mock.__str__ = lambda: 'mocked str'

  In [4]: str(mock)
  Out[4]: 'mocked str'


Interface Validations
---------------------

``StrictMock`` does a lot of validation under the hood to ensure you are configuring your mocks in conformity with the given template class interface. This has obvious immediate advantages, but is surprisingly helpful in catching bugs when refactoring happens (eg: the interface of the template class changed).

Attribute Existence
^^^^^^^^^^^^^^^^^^^

You won't be allowed to access or set an attribute to a ``StrictMock`` if the given template class does not have it:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class Calculator:
     ...:   def is_odd(self, x):
     ...:     return bool(x % 2)
     ...:

  In [3]: mock = StrictMock(template=Calculator)

  In [4]: mock.invalid
  (...)
  AttributeError: 'invalid' was not set for <StrictMock 0x7F4C62423F10 template=__main__.Calculator>.

  In [4]: mock.invalid = "whatever"
  (...)
  CanNotSetNonExistentAttribute: 'invalid' can not be set.
  <StrictMock 0x7F4C62423F10 template=__main__.Calculator> template class does not have this attribute so the mock can not have it as well.
  See also: 'runtime_attrs' at StrictMock.__init__.

Dynamic Attributes
""""""""""""""""""

This validation works even for attributes set by ``__init__``, as ``StrictMock`` introspects the code to learn about them:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
     ...:

  In [2]: class DynamicAttr(object):
     ...:     def __init__(self):
     ...:          self.dynamic = 'set from __init__'
     ...:

  In [3]: mock = StrictMock(template=DynamicAttr)

  In [4]: mock.dynamic = 'something else'

Methods
^^^^^^^

Only Accepts Callables
""""""""""""""""""""""

If the Template class attribute is a instance/class/static method, ``StrictMock`` will only allow callable values to be assigned:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class Calculator:
     ...:   def is_odd(self, x):
     ...:     return bool(x % 2)
     ...:

  In [3]: mock = StrictMock(template=Calculator)

  In [4]: mock.is_odd = "not callable"
  (...)
  NonCallableValue: 'is_odd' can not be set with a non-callable value.
  <StrictMock 0x7F4C62423F10 template=__main__.Calculator> template class requires this attribute to be callable.

Signatures
""""""""""

Method signatures must match the signature of the equivalent method at the template class:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class Calculator:
     ...:   def is_odd(self, x):
     ...:     return bool(x % 2)
     ...:

  In [3]: mock = StrictMock(template=Calculator)

  In [4]: mock.is_odd = lambda number, invalid: False

  In [5]: mock.is_odd(2, 'invalid')
  (...)
  TypeError: too many positional arguments

Magic Methods
"""""""""""""

Any magic methods defined at the template class will also have the safe by default characteristic:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class NotGreater:
     ...:     def __gt__(self, other):
     ...:         return False
     ...:

  In [3]: mock = StrictMock(template=NotGreater)

  In [4]: mock > 0
  (...)
  UndefinedAttribute: '__gt__' is not set.
  <StrictMock 0x7FE849B5DCD0 template=__main__.NotGreater> must have a value set for this attribute if it is going to be accessed.

Coroutine Functions (``async def``)
"""""""""""""""""""""""""""""""""""

Coroutine functions (whether instance, class or static methods) can only have a callable that returns an awaitable assigned:

.. code-block:: ipython

  In [1]: from testslide import StrictMock

  In [2]: class AsyncMethod:
     ...:     async def async_instance_method(self):
     ...:         pass
     ...:

  In [3]: mock = StrictMock(template=AsyncMethod)

  In [4]: def sync():
     ...:     pass
     ...:

  In [5]: mock.async_instance_method = sync

  In [6]: import asyncio

  In [7]: asyncio.run(mock.async_instance_method())
  (...)
  NonAwaitableReturn: 'async_instance_method' can not be set with a callable that does not return an awaitable.
  <StrictMock 0x7FACF5A974D0 template=__main__.AsyncMethod> template class requires this attribute to be a callable that returns an awaitable (eg: a 'async def' function).

Extra Functionality
-------------------

* ``copy.copy()`` and ``copy.deepcopy()`` works, and give back another StrictMock, with the same behavior.
* Template classes that use ``__slots__`` are supported.
