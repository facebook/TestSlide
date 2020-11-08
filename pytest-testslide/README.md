[TestSlide](https://testslide.readthedocs.io/) fixture for pytest.

## Quickstart

Install:

```
pip install pytest-testslide
```

In your test file:
```
        from pytest_testslide import testslide
        from testslide import StrictMock # if you wish to use StrictMock
        from testslide import matchers # if you wish to use Rspec style argument matchers
        .....
        testslide.mock_callable # to use mock_callable
        testslide.mock_async_callable # to use mock_async_callable
        testslide.mock_constructor # to use mock_constructor
        testslide.patch_attribute # to use patch_attribute

```

