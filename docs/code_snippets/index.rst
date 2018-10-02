Code Snippets
=============

Here are code snippets, to save you time when writing tests.

Atom
----

Please refer `Atom's documentation <http://flight-manual.atom.io/using-atom/sections/snippets/>`_ on how to use these.

.. code-block:: coffee-script

  '.source.python':
    ##
    ## TestSlide
    ##

    # Context
    '@context':
      'prefix': 'cont'
      'body': '@context\ndef ${1:context_description}(context):\n    ${2:pass}'
    '@fcontext':
      'prefix': 'fcont'
      'body': '@fcontext\ndef ${1:context_description}(context):\n    ${2:pass}'
    '@xcontext':
      'prefix': 'xcont'
      'body': '@xcontext\ndef ${1:context_description}(context):\n    ${2:pass}'
    '@context.sub_context':
      'prefix': 'scont'
      'body': '@context.sub_context\ndef ${1:context_description}(context):\n    ${2:pass}'
    '@context.fsub_context':
      'prefix': 'fscont'
      'body': '@context.fsub_context\ndef ${1:context_description}(context):\n    ${2:pass}'
    '@context.xsub_context':
      'prefix': 'xscont'
      'body': '@context.xsub_context\ndef ${1:context_description}(context):\n    ${2:pass}'
    '@context.shared_context':
      'prefix': 'shacont'
      'body': '@context.shared_context\ndef ${1:shared_context_description}(context):\n    ${2:pass}'

    # Example
    '@context.example':
      'prefix': 'exp'
      'body': '@context.example\ndef ${1:example_description}(self):\n    ${2:pass}'
    '@context.fexample':
      'prefix': 'fexp'
      'body': '@context.fexample\ndef ${1:example_description}(self):\n    ${2:pass}'
    '@context.xexample':
      'prefix': 'xexp'
      'body': '@context.xexample\ndef ${1:example_description}(self):\n    ${2:pass}'

    # Hooks
    '@context.before':
      'prefix': 'befo'
      'body': '@context.before\ndef ${1:before}(self):\n    ${2:pass}'
    '@context.after':
      'prefix': 'aft'
      'body': '@context.after\ndef ${1:after}(self):\n    ${2:pass}'
    '@context.around':
      'prefix': 'aro'
      'body': '@context.around\ndef ${1:around}(self, bef_aft_example):\n    ${2:pass  # before example}\n    bef_aft_example()\n    ${3:pass  # after example}'

    # Attributes
    '@context.memoize':
      'prefix': 'memo'
      'body': '@context.memoize\ndef ${1:attribute_name}(self):\n    ${2:pass}'
    '@context.function':
      'prefix': 'cfunc'
      'body': '@context.function\ndef ${1:function_name}(self):\n    ${2:pass}'