mock_callable()
===============

:doc:`../patch_attribute/index` deals with non-callable attributes. ``mock_callable()`` specializes on patching and mocking functions and instance/static/class methods. In a single shot, it allows you to:

* Create a callable mock.
* Define what call to accept.
* Define call behavior.
* Patch the callable mock somewhere.
* Define a call assertion (optional).

Sounds complicated, but it is not:

.. code-block:: python

  import os
  from testslide import TestCase

  def rm(path):
    os.remove(path)

  class TestRm(TestCase):
    def test_remove_from_filesystem(self):
      path = '/some/file'
      self.mock_callable(os, 'remove')\
        .for_call(path)\
        .to_return_value(None)\
        .and_assert_called_once()
      rm(path)

This test will **only** pass if ``os.remove`` was called once with ``path``. It will fail if ``os.remove``:

* Is not called.
* Is called more than once.
* Is called with any other argument.

For example, if the code is broken and does ``os.remove('/wrong/file')``:

.. code-block:: none

  $ testslide rm_test.py
  rm_test.TestRm
    test_remove_from_filesystem: AggregatedExceptions: 2 failures.

  Failures:

    1) rm_test.TestRm: test_remove_from_filesystem
      1) UnexpectedCallArguments: <module 'os' from '/opt/python/lib/python3.6/os.py'>, 'remove':
        Received call:
          ('/wrong/file',)
          {}
        But no behavior was defined for it.
        These are the registered calls:
          ('/some/file',)
          {}

        File "rm_test.py", line 14, in test_remove_from_filesystem
          rm(path)
        File "rm_test.py", line 5, in rm
          os.remove('/wrong/file')
        File "/opt/python/lib/python3.6/unittest/mock.py", line 939, in __call__
          return _mock_self._mock_call(*args, **kwargs)
        File "/opt/python/lib/python3.6/unittest/mock.py", line 1005, in _mock_call
          ret_val = effect(*args, **kwargs)
      2) AssertionError: calls did not match assertion.
      <module 'os' from '/opt/python/lib/python3.6/os.py'>, 'remove':
        expected: called at least 1 time(s) with arguments:
          ('/some/file',)
          {}
        received: 0 call(s)
        File "/opt/python/lib/python3.6/unittest/case.py", line 59, in testPartExecutor
          yield
        File "/opt/python/lib/python3.6/unittest/case.py", line 646, in doCleanups
          function(*args, **kwargs)

  Finished 1 example(s) in 0.0s
    Failed: 1

Note how you get two failed assertions, instead of just one:

* The mock was called with something unexpected.
* The expected call did not happen.

It is now pretty clear what is broken, and why it is broken.



Defining a Target
-----------------

You always start mock_callable with:

.. code-block:: python

  self.mock_callable(target, 'attribute_name')

``target`` can be:

* A :doc:`../../strict_mock/index`.
* A module.

  * The module can be given as a reference (eg: ``time``) or as a string (eg: ``"time"``). The latter allows you to avoid importing the module at the same file you use mock_callable.

* A Class
* Any object.

``attribute_name`` is the name of the function / method you want to mock.

.. note::

  You can mock instance methods at instances of classes but not at the class. This is by design, as mocking instance methods at the class affects every instance of that class, not just what's needed for the test, making it easy to introduce bugs. Assertions can be ambiguous: ``.and_assert_called_twice()`` means one instance called twice, or two instances called once each?

Defining Accepted Calls
-----------------------

By default, mock_callable accepts all call arguments:

.. code-block:: python

  self.mock_callable(os, 'remove')\
    .to_return_value(None)
  for n in range(3):
    os.remove(str(n)) # => None

You can define precisely what arguments to accept:

.. code-block:: python

  self.mock_callable(os, 'remove')\
    .for_call('/some/file')\
    .to_return_value(None)
  os.remove('/some/file') # => None
  os.remove('/some/other/file') # => raises UnexpectedCallArguments

Note how it is **safe by default**: once ``for_call`` is used, other calls will not be accepted.

.. note::

  Also check :doc:`../argument_matchers/index`: they allow more relaxed argument matching like "any string matching this regexp" or "any positive number".


For usecases where certain arguments could take many values, and setting up all the for_calls could become tedious you can use ``for_partial_call``
This causes Testslide to ignore all validations of args and kwargs passed to the mock, except those that are defined in the  ``for_partial_call``

Tests will still fail, if none of the necessary args or kwargs are passed, so this is a sane golden pathway, between writing safe and easy to use mocks.
Example:

.. code-block:: none

  def test_for_partial_call_accepts_all_other_args_and_kwargs(self):
      self.mock_callable(sample_module, "test_function",).for_partial_call(
          "firstarg", kwarg1="a"
      ).to_return_value(["blah"])
      sample_module.test_function("firstarg", "xx", kwarg1="a", kwarg2="x")

  def test_for_partial_call_fails_if_no_required_args_are_present(self):
      with self.assertRaises(mock_callable.UnexpectedCallArguments):
          self.mock_callable(sample_module, "test_function",).for_partial_call(
              "firstarg", kwarg1="a"
          ).to_return_value(["blah"])
          sample_module.test_function(
              "differentarg", "alsodifferent", kwarg1="a", kwarg2="x"
          )

  def test_for_partial_call_fails_if_no_required_kwargs_are_present(self):
      with self.assertRaises(mock_callable.UnexpectedCallArguments):
          self.mock_callable(sample_module, "test_function",).for_partial_call(
              "firstarg", kwarg1="x"
          ).to_return_value(["blah"])
          sample_module.test_function("firstarg", "secondarg", kwarg1="a", kwarg2="x")


Composition
^^^^^^^^^^^

You can use mock_callable for the same target as many times as needed, so you can compose the behavior you need:

.. code-block:: python

  self.mock_callable(os, 'remove')\
    .to_raise(FileNotFoundError)
  self.mock_callable(os, 'remove')\
    .for_call('/some/file')\
    .to_return_value(None)
  self.mock_callable(os, 'remove')\
    .for_call('/some/other/file')\
    .to_return_value(None)
  os.remove('/some/file') # => None
  os.remove('/some/other/file') # => None
  os.remove('/anything/else') # => raises FileNotFoundError

mock_callable scans the list of registered calls **from last to first**, until it finds a match (``UnexpectedCallArguments`` is raised if there's no match). In this example, ``FileNotFoundError`` essentially became the default behavior. This is particularly powerful when you configure it at the ``setUp()`` phase of your tests, then specialize the behavior inside each test function, for specific arguments.

Defining Call Behavior
----------------------

The **safe by default** rational spans to call behavior. There's no default, and you are required to define what happens when the call is made.

Returning a value
^^^^^^^^^^^^^^^^^

Always return the same value:

.. code-block:: python

  self.mock_callable(os, 'remove')\
    .for_call('/some/file')\
    .to_return_value(None)

Returning a series of values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Return each value from a list until exhausted:

.. code-block:: python

  self.mock_callable(time, 'time')\
    .to_return_values([1.0, 2.0, 3.0])
  time.time() => 1.0
  time.time() => 2.0
  time.time() => 3.0
  time.time() => raises UndefinedBehaviorForCall

Yielding values
^^^^^^^^^^^^^^^

You can return a generator with:

.. code-block:: python

  self.mock_callable(some_object, 'some_method_name')\
    .to_yield_values([1, 2, 3])
  for each_value in some_object.some_method_name():
    print(each_value)  # => 1, 2, 3

Raising exceptions
^^^^^^^^^^^^^^^^^^

You can raise exceptions by either giving an exception class itself or an instance of it:

.. code-block:: python

  self.mock_callable(some_object, 'some_method_name')\
    .to_raise(RuntimeError)
  some_object.some_method_name()  # => raise RuntimeError

Replacing the original implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace the original implementation with something else:

.. code-block:: python

  def func():
    return 33

  self.mock_callable(some_object, 'some_method_name')\
    .with_implementation(func)
  some_object.some_method_name()  # => 33

.. note::

  ``func`` can be any callable (eg: a lambda).

Wrapping the original implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When the target is a real object (not a mock), it can be useful to still call the original method, process its return perhaps, and return something else:

.. code-block:: python

  def trim_query(original_callable):
    return original_callable()[0:5]

  self.mock_callable(some_service, 'big_query')\
    .with_wrapper(trim_query)
  some_service.big_query()  # => returns trimmed list

Calling the original implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes it is useful to mock only cherry picked calls for real targets and allow all other calls through:

.. code-block:: python

  self.mock_callable(some_object, 'some_method')\
    .to_call_original()
  self.mock_callable(some_object, 'some_method')\
    .for_call('specific call')\
    .to_return_value('specific response')
  some_object.some_method('any call')  # => returns whatever some_object.some_method() returns
  some_object.some_method('specific call')  # => 'specific response'

You can achieve the opposite (specific call goes through, mocked general case) with:

.. code-block:: python

  self.mock_callable(some_object, 'some_method_name')\
    .to_return_value('general case')
  self.mock_callable(some_object, 'some_method_name')\
    .for_call('specific case')\
    .to_call_original()
  some_object.some_method_name('whatever')  # => 'general case'
  some_object.some_method_name('specific case')  # => Calls the original callable, and return the value

Defining Call Assertions
------------------------

When dealing with external dependencies, it is useful to assert on calls to them **when they have side-effects**. ``mock_callable()`` allows the easy assertion on such calls, as many times as needed within the same test.

Number of Calls
^^^^^^^^^^^^^^^

This will assert that the call was made exactly one time:

.. code-block:: python

    self.mock_callable(os, 'remove')\
      .for_call(path)\
      .to_return_value(None)\
      .and_assert_called_once()

Alternatively you may define an arbitrary exact number of calls, minimum, maximum or that no call should happen:

.. code-block:: python

  .and_assert_called_exactly(times)
  .and_assert_called_once()
  .and_assert_called_twice()
  .and_assert_called_at_least(times)
  .and_assert_called_at_most(times)
  .and_assert_called()
  .and_assert_not_called()

Call Order
^^^^^^^^^^

Frequently the order in which calls happen does not matter, but there are cases where this is desirable.

For example, let's say we want to ensure that some asset is first deleted from a storage index and then removed from the backend, thus avoiding the window of it being indexed, but unavailable at the backend. Here's how to do it:

.. code-block:: python

  self.mock_callable(storage_index, "delete")\
    .for_call(asset_id)\
    .and_assert_called_ordered()
  self.mock_callable(storage_backend, "delete")\
    .for_call(asset_id)\
    .and_assert_called_ordered()


For this test to pass, these calls must happen exactly in this order:

.. code-block:: python

  storage_index.delete(asset_id)
  storage_backend.delete(asset_id)

The test will fail if these calls are made in a different order or if they don't happen at all.

Cheat Sheet
-----------

It is a good idea to keep this at hand when using mock_callable:

.. code-block:: python

  self.mock_callable(target, 'callable_name')\
    # Call to accept
    .for_call(*args, **kwargs)\
    # Behavior
    .to_return_value(value)\
    .to_return_values(values_list)\
    .to_yield_values(values_list)\
    .to_raise(exception)\
    .with_implementation(func)\
    .with_wrapper(func)\
    .to_call_original()\
    # Assertion (optional)
    .and_assert_called_exactly(times)
    .and_assert_called_once()
    .and_assert_called_twice()
    .and_assert_called_at_least(times)
    .and_assert_called_at_most(times)
    .and_assert_called()
    .and_assert_called_ordered()
    .and_assert_not_called()

Magic Methods
-------------

Mocking magic methods (eg: ``__str__``) for an instance can be quite tricky, as ``str(obj)`` requires the mock to be made at ``type(obj)``. mock_callable implements the complicated mechanics required to make it work, so you can easily mock directly at instances:

.. code-block:: python

  import time
  from testslide import TestCase

  class A:
    def __str__(self):
      return 'original'

  class TestMagicMethodMocking(TestCase):
    def test_str(self):
      a = A()
      other_a = A()
      self.assertEqual(str(a), 'original')
      self.mock_callable(a, '__str__')\
        .to_return_value('mocked')
      self.assertEqual(str(a), 'mocked')
      self.assertEqual(str(other_a), 'original')

The mock works for the target instance, but does not affect other instances.



Type Validation
---------------

If typing annotation information is available, ``mock_callable()`` validates types of objects passing through the mock. If an invalid type is detected, it will raise ``testslide.lib.TypeCheckError``.

This feature is enabled by default. If you need to disable it (potentially due to a bug, please report!), you can do so by ``mock_callable(target, name, type_validation=False)``.

Call Argument Types
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

  import testslide, testslide.lib

  class SomeClass:
      def some_method(self, message: str):
          return "world"

  class TestArgumentTypeValidation(testslide.TestCase):
      def test_argument_type_validation(self):
          some_class_instance = SomeClass()
          self.mock_callable(some_class_instance, "some_method").to_return_value(
              "mocked world"
          )
          self.assertEqual(some_class_instance.some_method("hello"), "mocked world")
          with self.assertRaises(testslide.lib.TypeCheckError):
              # TypeCheckError: Call with incompatible argument types:
              # 'message': type of message must be str; got int instead
              some_class_instance.some_method(1)

This is particularly helpful when changes are introduced to the code: if a mocked method changes the signature, even when mocked, mock_callable will give you the signal that there's something broken.

Return Value Type
^^^^^^^^^^^^^^^^^

.. code-block:: python

  import testslide, testslide.lib

  class SomeClass:
      def one(self) -> int:
          return 1

  class TestReturnTypeValidation(testslide.TestCase):
      def test_return_type_validation(self):
          some_class_instance = SomeClass()
          self.mock_callable(some_class_instance, "one").to_return_value(
              "one"
          )
          with self.assertRaises(testslide.lib.TypeCheckError):
              # TypeCheckError: type of return must be int; got str instead
              some_class_instance.one()

Limitations
^^^^^^^^^^^

Currently `TypeVar` annotations are not being checked for.


Test Framework Integration
--------------------------

TestSlide's DSL
^^^^^^^^^^^^^^^

Integration comes out of the box for :doc:`../../testslide_dsl/index`: you can simply do ``self.mock_callable()`` from inside examples or hooks.

Python Unittest
^^^^^^^^^^^^^^^

``testslide.TestCase`` is provided with off the shelf integration ready:

- Inherit your ``unittest.TestCase`` from it.
- If you overload ``unittest.TestCase.setUp``, make **sure** to call ``super().setUp()`` before using ``mock_callable()``.

Any Test Framework
^^^^^^^^^^^^^^^^^^

You must follow these steps for **each** test executed that uses ``mock_callable()``:

* mock_callable calls ``testslide.mock_callable.register_assertion`` passing a callable object whenever an assertion is defined. You must set it to a function that will execute the assertion **after** the test code finishes. Eg: for Python's unittest: ``testslide.mock_callable.register_assertion = lambda assertion: self.addCleanup(assertion)``.
* After each test execution, you must **unconditionally** call ``testslide.mock_callable.unpatch_all_callable_mocks``. This will undo all patches, so the next test is not affected by them. Eg: for Python's unittest: ``self.addCleanup(testslide.mock_callable.unpatch_all_callable_mocks)``.
* You can then call ``testslide.mock_callable.mock_callable`` directly from your tests.
