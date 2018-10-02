Context Attributes and Functions
================================

Other than :doc:`../context_hooks/index`, you can also configure contexts with any attributes or functions.

Attributes
----------

You can set any arbitrary attribute from within any hook:

.. code-block:: python

  @context.before
  def before(self):
    self.calculator = Calculator()

and refer it later on:

.. code-block:: python

  @context.example
  def is_a_calculaor(self):
    assert type(self.calculator) == Calculator

Memoized Attributes
-------------------

Memoized attributes allow for lazy construction of attributes needed during a test. The attribute value will be constructed and remembered only at the first attribute access:

.. code-block:: python

  @context
  def Memoized_attributes(context):
  
    # This function will be used to lazily set a memoized attribute with the same name
    @context.memoize
    def memoized_value(self):
      return []
  
    # Lambdas are also OK
    context.memoize('another_memoized_value', lambda self: [])
  
    # Or in bulk
    context.memoize(
      yet_another=lambda self: 'one',
      and_one_more=lambda self: 'attr',
    )
  
    @context.example
    def can_access_memoized_attributes(self):
      # memoized_value
      assert len(self.memoized_value) == 0
      self.memoized_value.append(True)
      assert len(self.memoized_value) == 1

      # another_memoized_value
      assert len(self.another_memoized_value) == 0
      self.another_memoized_value.append(True)
      assert len(self.another_memoized_value) == 1

      # these were declared in bulk
      assert self.yet_anoter == 'one'
      assert self.and_one_more == 'attr'

Note in the example that the list built by ``memoized_value()``, is memoized, and is the same object for every access.

Another option is to force memoization to happen at a before hook, instead of at the moment the attribute is accessed:

.. code-block:: python

  @context.memoize_before
  def attribute_name(self):
    return []

In this case, the attribute will be set, regardless if it is used or not.

Composition
^^^^^^^^^^^

The big value of using memoized attributes as opposed to a regular attribute, is that you can easily do composition:

.. code-block:: python

  from testslide.dsl import context
  from testslide import StrictMock
  
  @context
  def Composition(context):
  
    context.memoize('attr_value', lambda self: 'default value')
  
    @context.memoize
    def mock(self):
      mock = StrictMock()
      mock.attr = self.attr_value
      return mock
  
    @context.example
    def sees_default_value(self):
      self.assertEqual(self.mock.attr, 'default value')
  
    @context.sub_context
    def With_different_value(context):
  
      context.memoize('attr_value', lambda self: 'different value')
  
      @context.example
      def sees_different_value(self):
        self.assertEqual(self.mock.attr, 'different value')

Functions
---------

You can define arbitrary functions that can be called from test code with the ``@context.function`` decorator:

.. code-block:: python

  @context
  def Arbitrary_helper_functions(context):
  
    @context.memoize
    def some_list(self):
      return []
  
    # You can define arbitrary functions to call later
    @context.function
    def my_helper_function(self):
      self.some_list.append('item')
      return "I'm helping!"
  
    @context.example
    def can_call_helper_function(self):
      assert "I'm helping!" == self.my_helper_function()
      assert ['item'] == self.some_list
