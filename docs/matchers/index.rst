Matchers
==========

Matchers provide a way to validate the arguments passed to :doc:`../mock_callable/index`, :doc:`../mock_async_callable/index` and :doc:`../mock_constructor/index`

Basic Usage
-----------------------


.. code-block:: python

  import testslide, backup, storage, matchers
  
  class TestBackupDelete(testslide.TestCase):
    def setUp(self):
      super().setUp()
      self.storage_mock = testslide.StrictMock(storage.Client)
      # Makes storage.Client(timeout=60) return self.storage_mock
      self.mock_constructor(storage, 'Client')\
        .for_call(timeout=matchers.ThisInt(60))\
        .to_return_value(self.storage_mock)
    def testrmjson(self)
      self.mock_callable(os, 'remove')\
          .for_call(matchers.RegexMatches(".*\.json))\
          .to_return_value(None)


Generic
-------

Any
^^^
testslide.matchers.Any() represents an argument, that anything

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.Any())\
          .to_return_value(None)




Integers
--------

AnyInt
^^^^^^
testslide.matchers.AnyInt() represents an argument, that matches any Integer

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.AnyInt())\
          .to_return_value(None)

ThisInt
^^^^^^^
testslide.matchers.ThisInt() represents an argument, that matches the specified Integer

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.ThisInt(60))\
          .to_return_value(None)

NotThisInt
^^^^^^^^^^
testslide.matchers.NotThisInt() represents an argument, that matches any Integer, but the specified one

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.NotThisInt(69))\
          .to_return_value(None)

IntBetween
^^^^^^^^^^
testslide.matchers.IntBetween() represents an argument, that matches any Integer, that falls in the specified range

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.IntBetween(59, 69))\
          .to_return_value(None)


IntGreater
^^^^^^^^^^
testslide.matchers.IntGreater() represents an argument, that matches any Integer, that is greater than the specified one

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.IntGreater(69))\
          .to_return_value(None)

IntGreaterOrEquals
^^^^^^^^^^^^^^^^^^
testslide.matchers.IntGreaterOrEquals() represents an argument than matches any Integer, that is greater than or equals the specified one

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.IntGreaterOrEquals(69))\
          .to_return_value(None)

IntLess
^^^^^^^
testslide.matchers.IntLess() represents an argument, that is less than the specified Integer

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.IntLess(69))\
          .to_return_value(None)

IntLessOrEquals
^^^^^^^^^^^^^^^
testslide.matchers.IntLessOrEquals() represents an argument, that is less than or equals the specified Integer

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.IntLessOrEquals(69))\
          .to_return_value(None)

Floats
------

AnyFloat
^^^^^^^^
testslide.matchers.() represents an argument, that matches any Float

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.AnyFloat())\
          .to_return_value(None)

ThisFloat
^^^^^^^^^
testslide.matchers.ThisFloat() represents an argument, that matches the specified Float

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.ThisFloat(6.0))\
          .to_return_value(None)

NotThisFloat
^^^^^^^^^^^^
testslide.matchers.NotThisFloat() represents an argument, that matches any Float, but the specified one

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.NotThisFloat(6.9))\
          .to_return_value(None)

FloatBetween
^^^^^^^^^^^^
testslide.matchers.FloatBetween() represents an argument, that matches any Float, that falls in the specified range

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.FloatBetween(5.9, 6.9))\
          .to_return_value(None)


FloatGreater
^^^^^^^^^^^^
testslide.matchers.FloatGreater() represents an argument, that matches any Float, that is greater than the specified one

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.FloatGreater(6.9))\
          .to_return_value(None)

FloatGreaterOrEquals
^^^^^^^^^^^^^^^^^^^^
testslide.matchers.FloatGreaterOrEquals() represents an argument, that matches any Float, that is greater than or equals the specified one

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.FloatGreaterOrEquals(6.9))\
          .to_return_value(None)

FloatLess
^^^^^^^^^
testslide.matchers.FloatLess() represents an argument, that is less than the specified Float

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.FloatLess(6.9))\
          .to_return_value(None)

FloatLessOrEquals
^^^^^^^^^^^^^^^^^
testslide.matchers.FloatLessOrEquals() represents an argument, that is less than or equals the specified Float

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(timeout=matchers.FloatLessOrEquals(6.9))\
          .to_return_value(None)


Strings
-------

AnyStr
^^^^^^
testslide.matchers.AnyStr() represents an argument, that matches any String


.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(matchers.AnyStr())\
          .to_return_value(None)

RegexMatches
^^^^^^^^^^^^
testslide.matchers.RegexMatches() represents an argument, that is a String and matches provided regular expression.


.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(matchers.RegexMatches(".*\.json"))\
          .to_return_value(None)


Collections
-----------

NotEmpty
^^^^^^^^
testslide.matchers.NotEmpty() represents an argument, that is a collection (eg: list, dict, tuple), and has elements.

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(matchers.NotEmpty())\
          .to_return_value(None)

Empty
^^^^^
testslide.matchers.NotEmpty() represents an argument, that is a collection (eg: list, dict, tuple), and has no elements.

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(matchers.Empty())\
          .to_return_value(None)

ListContaining
^^^^^^^^^^^^^^
testslide.matchers.NotEmpty() represents an argument, that is a list, and contains all the elements of the matcher.

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(matchers.ListContaining([1,2,3,"a"]))\
          .to_return_value(None)

DictContaining
^^^^^^^^^^^^^^
testslide.matchers.NotEmpty() represents an argument, that is a Dict, and has all the arguments of the matcher.

.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(matchers.Dict(["1":2,"3":"a"]))\
          .to_return_value(None)

Types
-----

A
^
testslide.matchers.A represent an argument, that matches if it has the same type as the matcher.


.. code-block:: python

  import testslide, backup, storage, matchers
  
    def testrmjson(self):
      self.mock_callable(os, 'remove')\
          .for_call(matchers.A(str)\
          .to_return_value(None)


More matchers?
--------------

Can't find the matcher you are looking for? Fork testslide, add your matcher and tests and send a PR.

Adding your matcher is easy:

.. code-block:: python

    class MyMatcher(_Matcher):
        def __eq__(self, other):
            return mycomparison(other)

If you want something a bit more, use _Richomparison as your baseclass, and let the baseclass do the heavy-lifting

.. code-block:: python

    class MyRichMatcher(_Richomparison):
        def __init__(self):
            super().__init__(klass=unicorn)
