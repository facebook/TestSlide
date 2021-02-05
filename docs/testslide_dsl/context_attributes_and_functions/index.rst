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

Attributes and sub-contexts
^^^^^^^^^^^^^^^^^^^^^^^^^^^

While it is very intuitive to do ``self.attr = "value"``, when used with sub-contexts there's potential for confusion:

.. code-block:: python

  from testslide.dsl import context
  
  @context
  def top_context(context):
  
    @context.before
    def set_attr(self):
      self.attr = "top context value"
      self.top_context_dict = {}
      self.top_context_dict["attr"] = self.attr
  
    @context.example
    def attr_is_the_same(self):
      self.assertEqual(self.attr, self.top_context_dict["attr"])
  
    @context.sub_context
    def sub_context(context):
      @context.before
      def reset_attr(self):
        self.attr = "sub context value"
        self.sub_context_dict = {}
        self.sub_context_dict["attr"] = self.attr
  
      @context.example
      def attr_is_the_same(self):
        self.assertEqual(self.attr, self.sub_context_dict["attr"])  # OK
        self.assertEqual(self.attr, self.top_context_dict["attr"])  # Boom!

In this example ``self.attr`` will have different values at ``top_context`` and ``sub_context`` resulting in some confusion in the assertions. These can be hard to spot in more complex scenarios, so TestSlide prevents attributes from being reset and the example above actually fails with ``AttributeError: Attribute 'attr' is already set.``.

The solution to this problem are **memoized attributes**.

Memoized Attributes
^^^^^^^^^^^^^^^^^^^

Memoized attributes are similar to a ``@property`` but with 2 key differences:

* Its value is materialized and cached on the first access.
* When multiple contexts define the same memoized attribute the inner-most overrides the outer-most definitions.

Let's see it in action:

.. code-block:: python

  from testslide.dsl import context
  
  @context
  def memoized_attributes(context):
  
    @context.memoize
    def memoized_list(self):
      return []
  
    @context.example
    def can_access_memoized_attributes(self):
      assert len(self.memoized_list) == 0  # list is materialized
      self.memoized_list.append(True)
      assert len(self.memoized_list) == 1  # same list is refereed

For the sake of convenience, memoized attributes can also be defined using lambdas:

.. code-block:: python

  context.memoize('memoized_list', lambda self: [])

or in bulk:

.. code-block:: python

  context.memoize(
    memoized_list=lambda self: [],
    yet_another_memoized_list=lambda self: [],
  )

In some cases, delaying the materialization of the attribute is not desired and it can be forced to happen unconditionally from within a before hook:

.. code-block:: python

  @context.memoize_before
  def memoized_list(self):
    return []

Overriding Memoized Attributes
""""""""""""""""""""""""""""""

As memoized attributes from parent contexts can be overridden by defining a new value from an inner context, it not only gives consistency on the attribute value, but also allows for some powerful composition:

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

This means, sub-contexts can be used to "tweak" values from a parent context.

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
