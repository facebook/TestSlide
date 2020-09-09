Context Hooks
=============

Contexts must prepare the test scenario according to its description. To do that, you can configure hooks to run before, after or around individual examples.

Before
------

Before hooks are executed in the order defined, before each example:

.. code-block:: python

  from testslide.dsl import context
  
  @context
  def before_hooks(context):
  
    @context.before
    def define_list(self):
      self.value = []
  
    @context.before
    def append_one(self):
      self.value.append(1)
  
    @context.before
    def append_two(self):
      self.value.append(2)
  
    @context.example
    def before_hooks_are_executed_in_order(self):
      self.assertEqual(self.value, [1, 2])

.. note::

  The name of the before functions does not matter. It is however useful to give them meaningful names, so they are easier to debug.

If code at a before hook fails (raises), test execution stops with a failure.

Typically, before hooks are used to:

* Setup the object being tested.
* Setup any dependencies, including mocks.

You can alternatively use lambdas as well:

.. code-block:: python

  @context
  def before_hooks(context):
  
    context.before(lambda self: self.value = [])

After
-----

The after hook is pretty much the opposite of before hooks: they are called *after* each example, in the **opposite** order defined:

.. code-block:: python

  from testslide.dsl import context
  import os
  
  @context
  def After_hooks(context):
  
    @context.after
    def do_call(self):
      os.remove('/tmp/something')
  
    @context.example
    def passes(self):
      self.mock_callable(os, 'remove')\
        .for_call('/tmp/something')\
        .to_return_value(None)\
        .and_assert_called_once()
  
    @context.example
    def fails(self):
      self.mock_callable(os, 'remove')\
        .for_call('/tmp/WRONG')\
        .to_return_value(None)\
        .and_assert_called_once()

After hooks are typically used for:

- Executing things common to all examples (eg: calling the code that is being tested).
- Doing assertions common to all examples.
- Doing cleanup logic (eg: closing file descriptors).

You can also define after hooks from within examples:

.. code-block:: python

  @context.example
  def can_define_after_hook(self):
    do_first_thing()

    @self.after
    def run_after_example_finishes(self):
      do_something_after_last_thing()

    do_last_thing()

Will run ``do_first_thing``, ``do_last_thing`` **then** ``do_something_after_last_thing``.

Aggregated failures
^^^^^^^^^^^^^^^^^^^

One important behavior of after hooks, is that they are **always** executed, regardless of any other failures in the test. This means, we get detailed result of each after hook failure:

.. code-block:: python

  from testslide.dsl import context
  
  @context
  def Show_aggregated_failures(context):
  
    @context.example
    def example_with_after_hooks(self):
      @self.after
      def assert_something(self):
        assert 1 == 2
  
      @self.after
      def assert_other_thing(self):
        assert 1 == 3

And its output:

.. code-block:: none

  Show aggregated failures
    example with after hooks: FAIL: AggregatedExceptions: empty example
  
  Failures:
  
    1) Show aggregated failures: example with after hooks
      1) AssertionError:
        (...)
      2) AssertionError:
        (...)
  
  Finished 1 examples in 0.0s
    Failed: 1

Around
------

Around hooks wrap around all **before hooks**, **example code** and **after hooks**:

.. code-block:: python

  from testslide.dsl import context
  import os, tempfile
  
  @context
  def Around_hooks(context):
  
    @context.around
    def inside_tmp_dir(self, wrapped):
      with tempfile.TemporaryDirectory() as path:
        self.path = path
        original_path = os.getcwd()
        try:
          os.chdir(path)
          wrapped()
        finally:
          os.chdir(original_path)
  
    @context.example
    def code_inside_temporary_dir(self):
      assert os.getcwd() == self.path

In this example, every example in the context will run inside a temporary directory.

If you declare multiple around hooks, the first around hook wraps the next one and so on.

Typical use for around hooks are similar to when context manager would be useful:

- Rolling back DB transactions after each test.
- Closing open file descriptors.
- Removing temporary files.