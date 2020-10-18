# Contributing to TestSlide

We want to make contributing to this project as easy and transparent as
possible.

## Our Development Process

All TestSlide development is public, and Facebook uses the public repository internally.

## Pull Requests

We actively welcome your pull requests.

1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. If you haven't already, complete the Contributor License Agreement ("CLA").

### Setting Up A Development Environment

Generally speaking:

- Install supported Python versions (see `.python-version`).
  - Using [pyenv](https://github.com/pyenv/pyenv) is highly advised!
- Enable the Python version defined at `tox.ini` `basepython`.
- Do `pip install tox` (and `tox-pyenv` if using pyenv).
- Run all tests: `tox`.

If you want more fine grained control over running tests you can:

- Create a venv: `python -m venv venv/`.
- Install deps: `pip install -e .`.
- Run individual tests:
  - `make tests/strict_mock_testslide.py`

`make` has other goodies:

- `V=1`: verbose output.
- `TESTSLIDE_FORMAT`: set the formatter (progress, documentation etc).
- `UNITTEST_VERBOSE=0`: disable verbose.

Here's a quick cookbook on how to have a Python installation working using Docker:

- Install [Docker CE](https://docs.docker.com/install/).
- Clone the repo: `git clone https://github.com/facebookincubator/TestSlide.git`.
- Create the Docker image: `docker create --name testslide --interactive --tty --mount type=bind,source="$PWD"/TestSlide,target=/root/src/TestSlide --workdir=/root/src/TestSlide debian /bin/bash`.
- Start a container with this image: `docker start --interactive testslide`.
- Install the dependencies: `apt update && apt -y install build-essential curl git libbz2-dev libncurses5-dev libreadline-dev libsqlite3-dev libssl-dev llvm vim wget zlib1g-dev`.
- Install pyenv: `curl https://pyenv.run | bash`.
- Add this to `~/.bashrc`:
```
export PATH="/root/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```
- Do `exec bash -i`.
- Install Python: `pyenv install $SUPPORTED_PYTHON_VERSION`.
- Enable the installed version `pyenv shell $SUPPORTED_PYTHON_VERSION`.

## Contributor License Agreement ("CLA")

In order to accept your pull request, we need you to submit a CLA. You only need
to do this once to work on any of Facebook's open source projects.

Complete your CLA here: <https://code.facebook.com/cla>

## Issues

We use GitHub issues to track public bugs. Please ensure your description is
clear and has sufficient instructions to be able to reproduce the issue.

Facebook has a [bounty program](https://www.facebook.com/whitehat/) for the safe
disclosure of security bugs. In those cases, please go through the process
outlined on that page and do not file a public issue.

## Coding Style  

We prefer using [Black](https://github.com/ambv/black) to format Python code.

## License

By contributing to TestSlide, you agree that your contributions will be licensed
under the LICENSE file in the root directory of this source tree.