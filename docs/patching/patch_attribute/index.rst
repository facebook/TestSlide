patch_attribute()
=================

``patch_attribute()`` will, for the duration of the test, change the value of a given attribute:

.. code-block:: python

  import math

  class ChangePi(TestCase):
    def test_pi(self):
      self.patch_attribute(math, "pi", 4)
      self.assertEqual(math.pi, 4)

``patch_attribute()`` works exclusively with **non-callable** attributes.


.. note::

	TestSlide provides :doc:`mock_callable()<../mock_callable/index>`, :doc:`mock_async_callable()<../mock_async_callable/index>` and :doc:`mock_constructor()<../mock_constructor/index>` for callables and classes because those require specific functionalities.

You can use ``patch_attribute()`` with:

- Modules.
- Classes.
- Instances of classes.
- Class attributes at instances of classes.
- Properties at instances of classes.

Properties are tricky to patch because of the quirky mechanics that `Python's Descriptor Protocol <https://docs.python.org/3/howto/descriptor.html>`_ requires. ``patch_attribute()`` has support for that so things "just work":

.. code-block:: python

  class WithProperty:
    @property
    def prop(self):
      return "prop"
  
  class PatchingProperties(TestCase):
    def test_property(self):
      with_property = WithProperty()
      self.patch_attribute(with_property, "prop", "mock")
      self.assertEqual(with_property.prop, "mock")

Type Validation
---------------

``patch_attribute`` implements type validation and will only allow attributes to be mocked with values of types that match the available typing annotation. ``TypeCheckerError`` will be raised if a bad type is given. This check is expected to work 100% of times, but if it does not (possibly a bug in TestSlide, please report!), you can disable it by ``doing patch_attribute(obj, "attr", "newval", type_validation=False)``.