Sharing Contexts
================

You can use shared contexts to avoid code duplication, and share common logic applicable to multiple contexts:

.. code-block:: python

  from testslide.dsl import context

  @context
  def Sharing_contexts(context):
  
      # This context will not be evaluated immediately, and can be reused later
      @context.shared_context
      def Shared_context(context):
  
          @context.example
          def shared_example(self):
              pass
  
      @context.sub_context
      def Merging_shared_contexts(context):
          # The shared context will me merged into current context
          context.merge_context('Shared context')
  
      @context.sub_context
      def Nesting_shared_contexts(context):
          # The shared context will be nested below the current context
          context.nest_context('Shared context')


And when we execute them:

.. code-block:: none

  Sharing contexts
    Merging shared contexts
      shared example: PASS
    Nesting shared contexts
      Shared context
        shared example: PASS
  
  Finished 2 examples in 0.0s:
    Successful: 2

Note the difference between merging and nesting a shared context: when you merge, no new sub context is created, when you nest, a new sub context will be created below where it was nested.

Parameterized shared contexts
-----------------------------

Your shared contexts can accept optional arguments, that can be used to control its declarations:

.. code-block:: python

  from testslide.dsl import context

  @context
  def Sharing_contexts(context):
  
      # This context will not be evaluated immediately, and can be reused later
      @context.shared_context
      def Shared_context(context, extra_example=False):
  
          @context.example
          def shared_example(self):
              pass
  
          if extra_example:
  
              @context.example
              def extra_shared_example(self):
                  pass
  
      @context.sub_context
      def With_extra_example(context):
          context.merge_context('Shared context', extra_example=True)
  
      @context.sub_context
      def Without_extra_example(context):
          context.nest_context('Shared context')

.. note::

  It is an anti-pattern to reference shared context arguments inside hooks or examples, as there's chance of leaking context from one example to the next.