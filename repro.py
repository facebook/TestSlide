from testslide.dsl import context
from testslide import StrictMock
import sys


class SomeClass:
    @staticmethod
    def sync_static_method(msg: str) -> bool:
        pass

    @staticmethod
    async def async_static_method(msg: str) -> bool:
        pass

    def sync_instance_method(self, msg: str) -> bool:
        pass

    async def async_instance_method(self, msg: str) -> bool:
        pass


@context
def top(context):
    @context.example
    def mock_sync_callable(self):
        self.mock_callable(SomeClass, "sync_static_method").for_call(
            "msg"
        ).to_return_value("boolean?")
        SomeClass.sync_static_method("msg")

    @context.example
    async def mock_async_callable(self):
        self.mock_async_callable(SomeClass, "async_static_method").for_call(
            "msg"
        ).to_return_value("boolean?")
        await SomeClass.async_static_method("msg")

    @context.example
    def strict_mock_sync_method(self):
        def sync_instance_method(msg: str) -> str:
            return "boolean?"

        mock = StrictMock(template=SomeClass)
        mock.sync_instance_method = sync_instance_method
        mock.sync_instance_method("msg")

    @context.example
    async def strict_mock_async_method(self):
        async def async_instance_method(msg: str) -> str:
            return "boolean?"

        mock = StrictMock(template=SomeClass)
        mock.async_instance_method = async_instance_method
        await mock.async_instance_method("msg")

    #
    # I don't think we support return validation for mock_constructor
    #
    # @context.example
    # async def mock_constructor(self):
    #   current_module = sys.modules[__name__]
    #   self.mock_constructor(current_module, 'SomeClass')\
    #     .for_call()\
    #     .to_return_value("an_instance_of_SomeClass")
    #   SomeClass()


##############
# HOW TO RUN #
##############

# $ python3 -m testslide.cli repro.py
# top
#   mock sync callable: TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:27)
#   mock async callable: TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:34)
#   strict mock sync method: TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:43)
#   strict mock async method: TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:51)

# Failures:

#   1) top: mock sync callable
#     1) TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:27)
#       File "repro.py", line 30, in mock_sync_callable
#         SomeClass.sync_static_method("msg")

#   2) top: mock async callable
#     1) TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:34)
#       File "/Users/fabriziocucci/.pyenv/versions/3.8.1/lib/python3.8/asyncio/runners.py", line 43, in run
#         return loop.run_until_complete(main)
#       File "/Users/fabriziocucci/.pyenv/versions/3.8.1/lib/python3.8/asyncio/base_events.py", line 612, in run_until_complete
#         return future.result()
#       File "repro.py", line 37, in mock_async_callable
#         await SomeClass.async_static_method("msg")

#   3) top: strict mock sync method
#     1) TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:43)
#       File "repro.py", line 45, in strict_mock_sync_method
#         mock.sync_instance_method("msg")

#   4) top: strict mock async method
#     1) TypeError: type of return must be bool; got str instead: 'boolean?' (at /Users/fabriziocucci/git/TestSlide/repro.py:51)
#       File "/Users/fabriziocucci/.pyenv/versions/3.8.1/lib/python3.8/asyncio/runners.py", line 43, in run
#         return loop.run_until_complete(main)
#       File "/Users/fabriziocucci/.pyenv/versions/3.8.1/lib/python3.8/asyncio/base_events.py", line 612, in run_until_complete
#         return future.result()
#       File "repro.py", line 53, in strict_mock_async_method
#         await mock.async_instance_method("msg")

# Finished 4 example(s) in 0.2s: .
#   Failed: 4
