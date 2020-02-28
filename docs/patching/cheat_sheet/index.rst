Cheat Sheet
===========

Here is a comprehensive list of use cases for all patching tools TestSlide offers and when to use each of them.


.. code-block:: python

  # module.py

  # self.patch_attribute(module, "MODULE_ATTRIBUTE", "mock")
  # module.MODULE_ATTRIBUTE  # => "mock"
  MODULE_ATTRIBUTE = "..."
  
  # self.mock_callable(module, "function_at_module")\
  #  .for_call()\
  #  .to_return_value(None)
  # module.function_at_module()  # => "mock"
  def function_at_module():
    pass
  
  # self.mock_callable(module, "async_function_at_module")\
  #  .for_call()\
  #  .to_return_value("mock")
  # await module.async_function_at_module()  # => "mock"
  async def async_function_at_module():
    pass
  
  # some_class_mock = testslide.StrictMock(template=module.SomeClass)
  class SomeClass:
    # Patching here affects all instances of the class as well
    # self.patch_attribute(SomeClass, "CLASS_ATTRIBUTE", "mock")
    # module.SomeClass.CLASS_ATTRIBUTE  # => "mock"
    CLASS_ATTRIBUTE = "..."
  
    # self.mock_constructor(module, "SomeClass")\
    #   .for_call()\
    #   .to_return_value(some_class_mock)
    # module.SomeClass()  # => some_class_mock
    def __init__(self):
      # Must be patched at instances
      self.init_attribute = "..."
  
    # Must be patched at instances
    @property
    def property(self):
      return "..."
  
    # Must be patched at instances
    def instance_method(self):
      pass
  
    # Must be patched at instances
    async def ainstance_method(self):
      pass
  
    # self.mock_callable(SomeClass, "class_method")\
    #  .for_call()\
    #  .to_return_value("mock")
    # module.SomeClass.class_method()  # => "mock"
    @classmethod
    def class_method(cls):
      pass
  
    # self.mock_async_callable(SomeClass, "async_class_method")\
    #  .for_call()\
    #  .to_return_value("mock")
    # await module.SomeClass.async_class_method()  # => "mock"
    @classmethod
    async def async_class_method(cls):
      pass
  
    # self.mock_callable(SomeClass, "static_method")\
    #  .for_call()
    #  .to_return_value("mock")
    # module.SomeClass.static_method()  # => "mock"
    @staticmethod
    def static_method(cls):
      pass
  
    # self.mock_async_callable(SomeClass, "async_static_method")\
    #  .for_call()
    #  .to_return_value("mock")
    # await module.SomeClass.async_static_method()  # => "mock"
    @staticmethod
    async def async_static_method(cls):
      pass
  
    # Must be patched at instances
    def __str__(self):
      return "SomeClass"
  
  some_class_instance = SomeClass()
  
  # self.patch_attribute(some_class_instance, "init_attribute", "mock")
  some_class_instance.init_attribute  # => "mock"
  
  # Patching at the instance does not affect other instances or the class
  # self.patch_attribute(some_class_instance, "CLASS_ATTRIBUTE", "mock")
  some_class_instance.CLASS_ATTRIBUTE  # => "mock"
  
  # self.patch_attribute(some_class_instance, "property", "mock")
  some_class_instance.property  # => "mock"
  
  # self.mock_callable(some_class_instance, "instance_method")\
  #  .for_call()\
  #  .to_return_value("mock")
  some_class_instance.instance_method()  # => "mock"
  
  # self.mock_async_callable(some_class_instance, "async_instance_method")\
  #  .for_call()\
  #  .to_return_value("mock")
  some_class_instance.async_instance_method()  # => "mock"
  
  # self.mock_callable(some_class_instance, "class_method")\
  #   .for_call()\
  #   .to_return_value("mock")
  some_class_instance.class_method()  # => "mock"
  
  # self.mock_async_callable(some_class_instance, "async_class_method")
  #   .for_call()\
  #   .to_return_value("mock")
  some_class_instance.async_class_method()  # => "mock"
  
  # self.mock_callable(some_class_instance, "static_method")\
  #  .for_call()\
  #  .to_return_value("mock")
  some_class_instance.static_method()  # => "mock"
  
  # self.mock_async_callable(some_class_instance, "async_static_method")\
  #  .for_call()\
  #  .to_return_value("mock")
  some_class_instance.async_static_method()  # => "mock"
  
  # self.mock_callable(some_class_instance, "__str__")\
  #   .for_call()\
  #   .to_return_value("mock")
  str(some_class_instance)  # => "mock"