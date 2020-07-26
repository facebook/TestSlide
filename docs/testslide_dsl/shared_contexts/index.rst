Sharing Contexts
================

Shared contexts allows sharing of common logic across different contexts. When you declare a shared context, its contents won't be evaluated, unless you either merge or nest it elsewhere. Let's see it in action.

Merging
-------

When you merge a shared context, its hooks and examples will be added to the existing context, alongside existing hooks and examples:

.. code-block:: python
  
  from testslide.dsl import context
  
  @context
  def Nesting_Shared_Contexts(context):
  
      @context.shared_context
      def some_shared_things(context):
  
          @context.before
          def do_common_thing_before(self):
              pass
  
          @context.example
          def common_example(self):
              pass
  
      @context.sub_context
      def when_one_thing(context):
          context.merge_context('some shared things')

          @context.before
          def do_one_thing_before(self):
              pass
  
          @context.example
          def one_thing_example(self):
              pass
  
      @context.sub_context
      def when_another_thing(context):
          context.merge_context('some shared things')
  
          @context.before
          def do_another_thing_before(self):
              pass
  
          @context.example
          def another_thing_example(self):
              pass

Will result in:

.. code-block:: none

  Nesting Shared Contexts
    when one thing
      common example
      one thing example
    when another thing
      common example
      another thing example
  
  Finished 4 example(s) in 0.0s
    Successful: 4

Nesting
-------

If you nest a shared context, another sub-context will be created, with the same name as the shared context, containing all the hooks and examples from the shared context:

.. code-block:: python
  
  from testslide.dsl import context
  
  @context
  def Nesting_Shared_Contexts(context):
  
      @context.shared_context
      def some_shared_things(context):
  
          @context.before
          def do_common_thing_before(self):
              pass
  
          @context.example
          def common_example(self):
              pass
  
      @context.sub_context
      def when_one_thing(context):
          context.nest_context('some shared things')
  
          @context.before
          def do_one_thing_before(self):
              pass
  
          @context.example
          def one_thing_example(self):
              pass
  
      @context.sub_context
      def when_another_thing(context):
          context.nest_context('some shared things')
  
          @context.before
          def do_another_thing_before(self):
              pass
  
          @context.example
          def another_thing_example(self):
              pass

Will result in:

.. code-block:: none

  Nesting Shared Contexts
    when one thing
      one thing example
      some shared things
        common example
    when another thing
      another thing example
      some shared things
        common example
  
  Finished 4 example(s) in 0.0s
    Successful: 4

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