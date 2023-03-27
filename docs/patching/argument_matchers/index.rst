Argument Matchers
=================

:doc:`mock_callable()<../mock_callable/index>`, :doc:`mock_async_callable()<../mock_async_callable/index>` and :doc:`mock_constructor()<../mock_constructor/index>` allow the definitions of what call arguments to accept by using ``.for_call()``. Eg:

.. code-block:: python

  self.mock_constructor(storage, 'Client')\
    for_call(timeout=60)\
    to_return_value(self.storage_mock)

This validation is strict: tests will work with ``Client(timeout=60)`` but fail with ``Client(timeout=61)``. Perhaps letting tests pass with "any positive integer" would be enough. This is precisely what **argument matchers** allow us to do:

.. code-block:: python

  from testslide.matchers import IntGreaterThan
  (...)
  self.mock_constructor(storage, 'Client')\
    for_call(timeout=IntGreaterThan(0))\
    to_return_value(self.storage_mock)

This matches for  ``Client(timeout=5)``, ``Client(timeout=60)`` but not for ``Client(timeout=0)`` or ``Client(timeout=-1)``.

Logic Operations
----------------

Argument matchers can be combined using bitwise operators:

.. code-block:: python

  # String containing "this" AND ending with "that"
  StrContaining("this") & StrEndingWith("that")
  # String containing "this" OR ending with "that"
  StrContaining("this") | StrEndingWith("that")
  # String containing "this" EXCLUSIVE OR ending with "that"
  StrContaining("this") ^ StrEndingWith("that")
  # String NOT containing "this"
  ~StrContaining("this")

Integers
--------

.. csv-table::
	:header: "Matcher", "Description"

	"``AnyInt()``", "Any ``int``"
	"``NotThisInt(value)``", "Any integer but the given value"
	"``IntBetween(min_value, max_valu)``", "Integer ``>= min_value`` and ``<= max_value``"
	"``IntGreaterThan(value)``", "Integer ``> value``"
	"``IntGreaterOrEquals(value)``", "Integer ``>= value``"
	"``IntLessThan(value)``", "Integer ``< value``"
	"``IntLessOrEquals(value)``", "Integer ``<= value``"

Floats
------

.. csv-table::
	:header: "Matcher", "Description"

	"``AnyFloat()``", "Any ``float``"
	"``NotThisFloat(value)``", "Any float but the given value"
	"``FloatBetween(min_value, max_valu)``", "Float ``>= min_value`` and ``<= max_value``"
	"``FloatGreaterThan(value)``", "Float ``> value``"
	"``FloatGreaterOrEquals(value)``", "Float ``>= value``"
	"``FloatLessThan(value)``", "Float ``< value``"
	"``FloatLessOrEquals(value)``", "Float ``<= value``"

Strings
-------

.. csv-table::
	:header: "Matcher", "Description"

	"``AnyStr()``", "Any ``str``"
	"``RegexMatches(pattern, flags=0)``", "Any string that matches the regular expression compiled by ``re.compile(pattern, flags)``"
	"``StrContaining(text)``", "A string which contains ``text`` in it"
	"``StrStartingWith()``", "A string that starts with ``text``"
	"``StrEndingWith(text)``", "A string that ends with ``text``"

Lists
-----

.. csv-table::
	:header: "Matcher", "Description"

	"``AnyList()``", "Any ``list``"
	"``ListContaining(element)``", "Any list containing ``element``"
	"``ListContainingAll(element_list)``", "Any list which contains every element of ``element_list``"
	"``NotEmptyList()``", "A list which has at least one element"
	"``EmptyList()``", "An empty list: ``[]``"

Dictionaries
------------

.. csv-table::
	:header: "Matcher", "Description"

	"``AnyDict()``", "Any ``dict``"
	"``NotEmptyDict()``", "A dictionary with any at least one key"
	"``EmptyDict()``", "An empty dictionary: ``{}``"
	"``DictContainingKeys(keys_list)``", "A dictionary containing all keys from ``keys_list``"
	"``DictSupersetOf(this_dict)``", "A dictionary containing all key / value pairs from ``this_dict``"

Collections
-----------
.. csv-table::
	:header: "Matcher", "Description"

	"``AnyContaining(element)``", "A container that contains ``element``"
	"``AnyContainingAll(element_list)``", "A container that contains every element of ``element_list``"
	"``AnyIterable()``", "Any iterable"
	"``IterableWithElements(element_list)``", "An iterable containing all the elements in ``element_list`` in the same order"
	"``AnyNotEmpty()``", "An object where ``len()`` does not evaluate to zero"
	"``AnyEmpty()``", "An object where ``len()`` evaluates to zero"

Generic
-------

.. csv-table::
	:header: "Matcher", "Description"

	"``Any()``", "Any object"
	"``AnyTruthy()``", "Any object where ``bool(obj) == True``"
	"``AnyFalsey()``", "Any object where ``bool(obj) == False``"
	"``AnyInstanceOf()``", "Any object where ``isinstance(obj) == True``"
	"``AnyWithCall(call)``", "Any object where ``call(obj) == True``"

.. code-block:: python

  self.mock_callable(os, 'remove')\
    .for_call(AnyWithCall(lambda path: path.endswith("py"))\
    .to_return_value(None)\
    .and_assert_called_once()
