Patching
========

:doc:`../../strict_mock/index` solves the problem of having mocks that behave like the real thing. To really accomplish that we need a way of defining what a mocked method call will return. We also need a way of putting the mock in place of real objects. These are problems solved with **patching**.

TestSlide provides patching tools specialized in different problems. They are not only useful to configure ``StrictMock``, but any Python object, including "real" ones, like a database connection. You can configure canned responses for specific calls, simulate network timeouts or anything you may need for your test.

Here's a summary of the patching tools available either via ``testslide.TestCase`` or :doc:`../testslide_dsl/index`. Also check the comprehensive :doc:`cheat_sheet/index`.


:doc:`patch_attribute()<patch_attribute/index>`
	Changes the value of an attribute. Eg:

	.. code-block:: python

		self.patch_attribute(math, "pi", 3)
		math.pi  # => 3

:doc:`mock_callable()<mock_callable/index>` / :doc:`mock_async_callable()<mock_async_callable/index>`
	Similar to ``patch_attribute()`` but designed to work with sync/async **functions/methods**. It creates and patches mocks for callables, which implements call **arguments constraints**, different call **behaviors** (return value, raise exception etc) and optional **call assertions**. Eg:

	.. code-block:: python

		self.mock_callable("os.path", "exists")\
		  .for_call("/bin")\
		  .to_return_value(False)
		os.path.exists("/bin")  # => False

:doc:`mock_constructor()<mock_constructor/index>`
	Allows classes to return mocks when new instances are created instead of real instances. It has the same fluid interface as ``mock_callable()``/``mock_async_callable()``. Eg:

	.. code-block:: python

		popen_mock = StrictMock(template=subprocess.Popen)
		self.mock_constructor(subprocess, "Popen")\
		  .for_call(["/bin/true"])\
		  .to_return_value(popen_mock)
		subprocess.Popen(["/bin/true"])  # => popen_mock

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   patch_attribute/index.rst
   mock_callable/index.rst
   mock_async_callable/index.rst
   mock_constructor/index.rst
   argument_matchers/index.rst
   cheat_sheet/index.rst