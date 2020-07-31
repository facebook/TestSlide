``unittest.TestCase`` Integration
=================================

TestSlide's DSL builtin integration with `Python's unittest <https://docs.python.org/3/library/unittest.html>`_.

Assertions
----------

TestSlide (currently) has no assertion framework. It comes however, with all ``self.assert*`` methods that you find at ``unittest.TestCase`` (`see the docs <https://docs.python.org/3/library/unittest.html#assert-methods>`_):

.. code-block:: python

  @context
  def unittest_assert_methods(context):
  
    @context.example
    def has_assert_true(self):
      self.assertTrue(True)

Reusing existing ``unittest.TestCase`` setUp
--------------------------------------------

You can leverage existing ``unittest.TestCase`` classes, and use their setup logic to with TestSlide's DSL:

.. code-block:: python

  @context
  def merging_test_cases(context):

    context.merge_test_case(SomePreExistingTestCase, 'legacy_test_case')

    @context.example
    def can_access_the_test_case(self):
      self.legacy_test_case  # => SomePreExistingTestCase instance

``merge_test_case`` will call all ``SomePreExistingTestCase`` test hooks (``setUp``, ``tearDown`` etc) for each example.

From each example (or hooks), you will have access to the ``TestCase`` instance, so you can access any of its methods or attributes.

.. note::

  Only hooks are executed, no existing tests will be imported!
