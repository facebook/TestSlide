Contexts and Examples
=====================

Within TestSlide's DSL language, a single test is called an **example**. All examples are declared inside a **context**. Contexts can be arbitrarily nested.

**Contexts** hold code that sets up and tear down the environment for each particular scenario. Things like instantiating objects and setting up mocks are usually part of the context.

**Examples** hold only code required to test the particular case.

Let's see it in action:

.. code-block:: python

  from testslide.dsl import context
  
  @context
  def calculator(context):
  
      @context.sub_context
      def addition(context):
  
          @context.example
          def sums_given_numbers(self):
              pass
  
      @context.sub_context
      def subtract(context):
  
          @context.example
          def subtracts_given_numbers(self):
              pass


This describes the basic behavior of a calculator class. Here's what you get when you run it:

.. code-block:: python

  calculator
    addition
      sums given numbers: PASS
    subtraction
      subtracts given numbers: PASS
  
  Finished 2 examples in 0.0s
    Successful: 2

Note how TestSlide parses the Python code, and yields a close to spoken language version of it.

Sub Examples
------------

Sometimes, within the same example, you want to exercise your code multiple times for the same data. Sub examples allow you to do just that:

.. code-block:: python

  from testslide.dsl import context

  @context
  def Sub_examples(context):

    @context.example
    def shows_individual_failures(self):
      for i in range(5):
        with self.sub_example():
          if i %2:
            raise AssertionError('{} failed'.format(i))
      raise RuntimeError('Last Failure')


When executed, TestSlide understands all cases, and report them properly:

.. code-block:: none

  Sub examples
    shows individual failures: AggregatedExceptions: 3 failures.
  
  Failures:
  
    1) Sub examples: shows individual failures
      1) RuntimeError: Last Failure
        File "sub_examples_test.py", line 12, in shows_individual_failures
          raise RuntimeError('Last Failure')
      2) AssertionError: 1 failed
        File "sub_examples_test.py", line 11, in shows_individual_failures
          raise AssertionError('{} failed'.format(i))
      3) AssertionError: 3 failed
        File "sub_examples_test.py", line 11, in shows_individual_failures
          raise AssertionError('{} failed'.format(i))
  
  Finished 1 example(s) in 0.0s
    Failed: 1

Explicit names
--------------

TestSlide extracts the name for contexts and examples from the function name, just swapping ``_`` for a space. If you need special characters at your context or example names, you can do it like this:

.. code-block:: python

  from testslide.dsl import context

  @context('Top-level context name')
  def top(context):
    @context.sub_context('sub-context name')
    def sub(context):
      @context.example('example with weird-looking name')
      def ex(self):
        pass

.. note::

  When explicitly naming, the function name is irrelevant, just make sure there's no name collision.