[TestSlide](https://testslide.readthedocs.io/) fixture for pytest.

## Quickstart

Install:

```
pip install pytest-testslide
```

In your test file:
```
        import pytest
        from pytest_testslide import testslide
        from testslide import StrictMock # if you wish to use StrictMock
        from testslide import matchers # if you wish to use Rspec style argument matchers
        .....
        def test_mock_callable_patching_works(testslide):
            testslide.mock_callable(time, "sleep").to_raise(RuntimeError("Mocked!")) #mock_callable
            with pytest.raises(RuntimeError):
                time.sleep()

        @pytest.mark.asyncio
        async def test_mock_async_callable_patching_works(testslide):
            testslide.mock_async_callable(sample_module.ParentTarget, "async_static_method").to_raise(RuntimeError("Mocked!")) #mock_async_callable
            with pytest.raises(RuntimeError):
                await sample_module.ParentTarget.async_static_method("a", "b")

        def test_mock_constructor_patching_works(testslide):
            testslide.mock_constructor(sample_module, "ParentTarget").to_raise(RuntimeError("Mocked!"))  #mock_constructor
            with pytest.raises(RuntimeError):
                sample_module.ParentTarget()

        def test_patch_attribute_patching_works(testslide):
            testslide.patch_attribute(sample_module.SomeClass, "attribute", "patched") #patch_attribute
            assert sample_module.SomeClass.attribute == "patched"

```

