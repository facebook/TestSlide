Skip and Focus
==============

The :doc:`../../test_runner/index` supports focusing and skipping examples. Let's see how to do it with TestSlide's DSL.

Focus
-----

You can focus either the top level context, sub contexts or examples by prefixing their declaration with a ``f``:

.. code-block:: python

  from testslide.dsl import context, fcontext, xcontext
  
  @context
  def Focusing(context):
  
    @context.example
    def not_focused_example(self):
      pass
  
    @context.fexample
    def focused_example(self):
      pass
  
    @context.sub_context
    def Not_focused_subcontext(context):
  
      @context.example
      def not_focused_example(self):
        pass
  
    @context.fsub_context
    def Focused_context(context):
  
      @context.example
      def inherits_focus_from_context(self):
        pass

And when run with ``--focus``:

.. code-block:: none

  Focusing
    *focused example: PASS
    *Focused context
      *inherits focus from context: PASS
  
  Finished 2 example(s) in 0.0s
    Successful:  2
    Not executed:  2

Skip
----

Skipping works just the same, but you have to use a ``x``:

.. code-block:: python

  from testslide.dsl import context, fcontext, xcontext
  
  @context
  def Skipping(context):
  
    @context.example
    def not_skipped_example(self):
      pass
  
    @context.xexample
    def skipped_example(self):
      pass
  
    @context.example(skip=True)
    def skipped_example_from_arg(self):
      pass
  
    @context.example(skip_unless=False)
    def skipped_example_from_unless_arg(self):
      pass
  
    @context.sub_context
    def Not_skipped_subcontext(context):
  
      @context.example
      def not_skipped_example(self):
        pass
  
    @context.xsub_context
    def Skipped_context(context):
  
      @context.example
      def inherits_skip_from_context(self):
        pass

.. code-block:: none

  Skipping
    not skipped example: PASS
    skipped example: SKIP
    skipped example from arg: SKIP
    skipped example from unless arg: SKIP
    Not skipped subcontext
      not skipped example: PASS
    Focused context
      inherits focus from context: SKIP
  
  Finished 4 example(s) in 0.0s
    Successful:  2
    Skipped:  2
