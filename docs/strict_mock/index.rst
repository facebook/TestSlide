StrictMock
==========

When unit testing, mocks are often used in place of a real dependency, so tests can run independently. Mocks must behave exactly like the real thing, by returning configured canned responses, but rejecting anything else. If this is not true, it is hard to trust your test results.

Let's see a practical example of that:

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

The mock, right after being created, already has dangerous behavior. When ``is_odd()`` is called, another mock is returned. And it is unconditionally ``True``. And this is wrong: 2 is **not** odd. When this happens in your test, it is hard to trust its results: it might go green, even with buggy code. Also note how the mock accepts calls with any arguments, even if they don't match the original method signature.

A Well Behaved Mock
-------------------

StrictMock is **safe by default**: it only has configure behavior:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
  
  In [2]: class Calculator:
     ...:   def is_odd(self, x):
     ...:     return bool(x % 2)
     ...:   
  
  In [3]: mock = StrictMock(Calculator)
  
  In [4]: mock.is_odd(2)
  (...)
  UndefinedBehavior: <StrictMock 0x7F290A3DD860 template=__main__.Calculator>:
    Attribute 'is_odd' has no behavior defined.
    You can define behavior by assigning a value to it.

Instead of guessing what ``is_odd`` should return, StrictMock clearly tells you it was not told what to do with it. In this case, the mock is clearly missing the behavior, that we can trivially add:

.. code-block:: ipython

  In [5]: mock.is_odd = lambda number: False
  
  In [6]: mock.is_odd(2)
  Out[6]: False

API Validations
---------------

StrictMock does a lot of validation under the hood, so you can trust its behavior, even when breaking changes are introduced.

Attribute Existence
^^^^^^^^^^^^^^^^^^^

You won't be allowed to set an attribute to a StrictMock if the given template class does not have it:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
  
  In [2]: class Calculator:
     ...:   def is_odd(self, x):
     ...:     return bool(x % 2)
     ...:   
  
  In [3]: mock = StrictMock(Calculator)
  
  In [4]: mock.invalid = 'whatever'
  (...)
  NoSuchAttribute: <StrictMock 0x7F7821920780 template=__main__.Calculator>:
    No such attribute 'invalid'.
    Can not set attribute invalid that is neither part of template class Calculator or runtime_attrs=[].

Dynamic Attributes
""""""""""""""""""

StrictMock will introspect at the template class code, to detect attributes that are dynamically defined:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
     ...: 
  
  In [2]: class DynamicAttr(object):
     ...:     def __init__(self):
     ...:          self.dynamic = 'set from __init__'
     ...:          
  
  In [3]: mock = StrictMock(DynamicAttr)
  
  In [4]: mock.dynamic = 'something else'

.. note::

  This feature is **not** available in Python 2!

The detection mechanism can only detect attributes defined from ``__init__``. If you have attributes defined at other places, you will need to inform them explicitly:

.. code-block:: python

  StrictMock(TemplateClass, runtime_attrs=['attr_name'])

Method Signatures
^^^^^^^^^^^^^^^^^

StrictMock also ensures that method signatures match the ones from the template class:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
  
  In [2]: class Calculator:
     ...:   def is_odd(self, x):
     ...:     return bool(x % 2)
     ...:   
  
  In [3]: mock = StrictMock(Calculator)
  
  In [4]: mock.is_odd = lambda number, invalid: False
  
  In [5]: mock.is_odd(2, 'invalid')
  (...)
  TypeError: too many positional arguments

.. note::

  This feature is **not** available in Python 2!

Magic Methods
-------------

Defining behavior for magic methods works out of the box:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
  
  In [2]: mock = StrictMock()
  
  In [3]: mock.__str__ = lambda: 'mocked str'
  
  In [4]: str(mock)
  Out[4]: 'mocked str'

Naming
------

You can optionally name your mock, to make it easier to identify:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
  
  In [2]: str(StrictMock())
  Out[2]: '<StrictMock 0x7F7A30FC0748>'
  
  In [3]: str(StrictMock(name='whatever'))
  Out[3]: "<StrictMock 0x7F7A30FDFF60 name='whatever'>"

Generic Mocks
-------------

It is recommended to use StrictMock giving it a template class, so you can leverage its API validation. There are situations however, that any "generic mock" is good enough. You can still use StrictMock, although you'll loose most validations:

.. code-block:: ipython

  In [1]: from testslide import StrictMock
  
  In [2]: mock = StrictMock()
  
  In [3]: mock.whatever
  (...)
  UndefinedBehavior: <StrictMock 0x7FED1C724C18>:
    Attribute 'whatever' has no behavior defined.
    You can define behavior by assigning a value to it.
  
  In [4]: mock.whatever = 'something'
  
  In [5]: mock.whatever
  Out[5]: 'something'

It will accept setting any attributes, with any values.

Extra Functionality
-------------------

* ``copy.copy()`` and ``copy.deepcopy()`` works, and give back another StrictMock, with the same behavior.
* Template classes that use ``__slots__`` are supported.
* If the template class is a context manager, the StrictMock instance will also define ``__enter__``, yielding itself, and an empty ``__exit__``.