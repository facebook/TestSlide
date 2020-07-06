Test Runner
===========

TestSlide has its own :doc:`DSL<../testslide_dsl/index>` that you can use to write tests, and so it comes with its own test runner. However, it can also execute tests written for `Python's unittest <https://docs.python.org/3/library/unittest.html>`_, so you can have its benefits, without having to rewrite everything.

To use, simply give it a list of ``.py`` files containing the tests:

.. code-block:: none

  $ testslide calculator_test.py
  calculator_test.TestCalculatorAdd
    test_add_negative: PASS
    test_add_positive: PASS
  calculator_test.TestCalculatorSub
    test_sub_negative: PASS
    test_sub_positive: PASS
  
  Finished 4 example(s) in 0.0s
    Successful:  4

.. note::

  For documentation simplicity, the output shown here is monochromatic and boring. When executing TestSlide from a terminal, it is **colored**, making it significantly easier to read. Eg: green for success, red for failure.

Whatever ``unittest.TestCase`` or :doc:`DSL<../testslide_dsl/index>` declared in the given files will be executed. You can even mix them in the same project or file.

.. note::

  When using :doc:`../patching/patch_attribute/index`, :doc:`../patching/mock_callable/index` or :doc:`../patching/mock_constructor/index` you must inherit your test class from ``testslide.TestCase`` to have access to those methods. The test runner does **not** require that, and is happy to run tests that inherit directly (or indirectly) from ``unittest.TestCase``.

.. note::

  Tests inheriting from ``testslide.TestCase`` can **also** be executed by Python's unittest `CLI <https://docs.python.org/3/library/unittest.html#command-line-interface>`_.

Listing Available Tests
-----------------------

You can use ``--list`` to run test discovery and list all tests found:

.. code-block:: none

  $ testslide --list backup_test.py
  backup_test.TestBackupDelete: test_delete_from_storage

Multiple Failures Report
------------------------

When using TestSlide's :doc:`../patching/mock_callable/index` assertions, you can have a better signal on failures. For example, in this test we have two assertions:

.. code-block:: python

  def test_delete_from_storage(self):
    self.mock_callable(self.storage, 'delete')\
      .for_call('/file').to_return_value(True)\
      .and_assert_called_once()
    self.assertEqual(Backup().delete('/file'), True)

Normally when a test fails, you get only signal from the first failure. TestSlide's Test Runner can understand what you meant, and give you a more comprehensive signal, telling about each failed assertion:

.. code-block:: none

  $ testslide backup_test.py
  backup_test.TestBackupDelete
    test_delete_from_storage: AssertionError: <StrictMock 0x7F55C5159B38 template=storage.Client>,   'delete':
  
  Failures:

  1) backup_test.TestBackupDelete: test_delete_from_storage
    1) AssertionError: None != True
      File "backup_test.py", line 47, in test_delete
        self.assertEqual(Backup().delete('/file’), True)
      File "/opt/python3.6/unittest/case.py", line 829, in assertEqual
        assertion_func(first, second, msg=msg)
      File "/opt/python3.6/unittest/case.py", line 822, in _baseAssertEqual
        raise self.failureException(msg)
    2) AssertionError: <StrictMock 0x7F55C5159B38 template=storage.Client>, 'delete':
      expected: called exactly 1 time(s) with arguments:
        ('/file',)
        {}
      received: 0 call(s)
      File "/opt/python3.6/unittest/case.py", line 59, in testPartExecutor
        yield
      File "/opt/python3.6/unittest/case.py", line 646, in doCleanups
        function(*args, **kwargs)

Failing Fast
------------

When you change something and too many tests break, it is useful to stop the execution at the first failure, so you can iterate easier. To do that, use the ``--fail-fast`` option.

Focus and Skip
--------------

TestSlide allows you to easily focus execution of a single test, by simply adding ``f`` to the name of the test function:

.. code-block:: python

  def ftest_sub_positive(self):
    self.assertEqual(
      Calc().sub(1, 1), 0
    )

And then run your tests with ``--focus``:

.. code-block:: none

  $ testslide --focus calc_test.py
  calc.TestCalcSub
    *ftest_sub_positive: PASS
  
  Finished 1 example(s) in 0.0s
    Successful: 1
    Not executed: 3

Only ``ftest`` tests will be executed. Note that it also tells you how many tests were not executed.

When you are committing tests to a continuous integration system, focusing tests may not be the best choice. You can
use the cli option ``--fail-if-focused`` which will cause TestSlide to fail if any focused examples are run.

Similarly, you can skip a test with ``x``:

.. code-block:: python

  def xtest_sub_positive(self):
    self.assertEqual(
      Calc().sub(1, 1), 0
    )

And this test will be skipped:

.. code-block:: none

  $ testslide calc_test.py
  calc.TestCalcAdd
    test_add_negative: PASS
    test_add_positive: PASS
  calc.TestCalcSub
    test_sub_negative: PASS
    xtest_sub_positive: SKIP
  
  Finished 4 example(s) in 0.0s
    Successful: 3
    Skipped: 1

Path Simplification
-------------------

The option ``--trim-path-prefix`` selects a path prefix to remove from stack traces and error messages. This makes parsing error messages easier. It defaults to the working directory, so there's seldom need to tweak it.

Internal Stack Trace
--------------------

By default, stack trace lines that are from TestSlide's code base are hidden, as they are only useful when debugging TestSlide itself. You can see them if you wish, by using ``--show-testslide-stack-trace``.

Shuffled Execution
------------------

Each test must be independent and isolated from each other. For example, if one test manipulates some module level object, that the next test depends on, we are leaking the context of one test to the next. To catch such cases, you can run your tests with ``--shuffle``: tests will be executed in a random order every time. The test signal must always be the same, no matter in what order tests run. You can tweak the seed with ``--seed``.

Slow Imports Profiler
---------------------

As projects grow with more dependencies, running a test for a few lines of code can take several seconds. This is often cause by time spent on importing dependencies, rather that the tests themselves. If you run your tests with ``--import-profiler $MS``, any imported module that took more that that the given amount of milliseconds will be reported in a nice and readable tree view. This helps you optimize your imports, so your unit tests can run faster. Frequently, the cause of slow imports is the construction of heavy objects at module level.

Code Coverage
-------------

`Coverage.py <https://coverage.readthedocs.io/en/coverage-5.1/>`_ integration is simple. Make sure your ``.coveragerc`` file has this set:

.. code-block:: ini

  [run]
  parallel = True

and then you can run all your tests and get a report like this

.. code-block:: shell

  $ coverage erase
  $ COVERAGE_PROCESS_START=.coveragerc testslide some.py tests.py
  $ COVERAGE_PROCESS_START=.coveragerc testslide some_more_tests.py
  $ coverage combine
  $ coverage report

Tip: Automatic Test Execution
-----------------------------

To help iterate even quicker, you can pair ``testslide`` execution with `entr <http://www.entrproject.org/>`_ (or any similar):

.. code-block:: none

  find . -name \*.py | entr testslide tests/.py

This will automatically execute all your tests, whenever a file is saved. This is particularly useful when paired with focus and skip. This means **you don't have to leave your text editor, to iterate over your tests and code**.
