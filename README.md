# TestSlide

TestSlide is a test framework for Python that makes mocking and iterating over code with tests a breeze. It has several components, that you can use *all together* or *stand alone*, even with *other test frameworks*.

## Example

Let's say we have the following backup client we want to test, that depends on some storage backend:

```python
# backup.py

import storage

class Backup:
	def __init__(self):
		self.storage = storage.Client(timeout=60)

	def delete(self, path):
		self.storage.delete(path)
```

Here's a comprehensive example, that uses all of TestSlide's components to test it:

```python
# backup_test.py

from testslide.dsl import context
import storage
import backup

# We declare a context for what we want to test
@context
def Backup(context):

	# Inside the context, we say it'll have an attribute "backup", our target.
	# Note it is declared as a lambda, so it will be evaluated for each example.
	context.memoize("backup", lambda self: backup.Backup())

	# This is the mock for the storage backend, that'll need to patch at
	# storage.Client's constructor (below)
	context.memoize("storage", lambda self: StrictMock(storage.Client))

	# Before executing each example, storage.Client constructor will be mocked
	# to return its mock instead.
	@context.before
	def mock_storage_Client(self):
		# With this, Client's constructor will return the mock, *only* when
		# called with timeout=60. If any other call is received, the test
		# will fail.
		self.mock_constructor(storage, 'Client')\
			.for_call(timeout=60)\
			.to_return_value(self.storage)

	# We now nest another context, specifying we are testing the delete method.
	@context.sub_context
	def delete(context):
		context.memoize("path", lambda self: '/some/file')

		# After every example within this delete context, we want to call
		# Backup.delete
		@context.after
		def call_backup_delete(self):
			self.backup.delete(self.path)

		# Having all the context setup, we can now focus on the example,
		# that's gonna test that Backup.delete deletes the file on the
		# storage backend.
		@context.example
		def it_deletes_from_storage_backend(self):
			# This mocks the storage backend to accept the delete call, and
			# also creates an assertion that it must have happened exactly
			# once. The test will fail if the call does not happen, happens
			# more than once or happens with different arguments.
			self.mock_callable(self.storage, 'delete')\
				.for_call(self.path)\
				.to_return_value(True)\
				.and_assert_called_once()
```

## Requirements

TestSlide is validated to work with:

* Linux
* Python 2 / 3

## Building TestSlide

TODO

## Installing TestSlide

TODO pip install testslide

## How TestSlide works
...

## Full documentation

TODO link to Wiki

## Join the TestSlide community

* Website: https://github.com/facebookincubator/TestSlide
See the CONTRIBUTING file for how to help out.

## License
TestSlide is MIT licensed, as found in the LICENSE file.