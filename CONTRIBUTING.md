# Contributing to TestSlide

We want to make contributing to this project as easy and transparent as
possible.

## Our Development Process

All TestSlide development is public, and Facebook uses the public repository internally.

## Pull Requests

We actively welcome your pull requests.

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. If you haven't already, complete the Contributor License Agreement ("CLA").

### Setting Up A Development Environment

Generally speaking:

- Install a supported Python version (see `.github/workflows/build.yml`) (suggestion: use [pyenv](https://github.com/pyenv/pyenv)).
- Install the dependencies: `make install_build_deps`.
- Run the tests: `make` (or `make V=1` for verbose output).

Here's a quick cookbook on how to have a Python installation working using Docker:

1. Install [Docker CE](https://docs.docker.com/install/).
2. Clone the repo
    ```shell
    git clone https://github.com/facebook/TestSlide.git
    ```
3. Create the Docker image:
    ```shell
    docker create --name testslide --interactive --tty --mount type=bind,source="$PWD"/TestSlide,target=/root/src/TestSlide --workdir=/root/src/TestSlide debian /bin/bash
    ```
4. Start a container with this image:
    ```shell
    docker start --interactive testslide
    ```
5. Install the dependencies:
    ```shell
    apt update && apt -y install build-essential curl git libbz2-dev libncurses5-dev libreadline-dev libsqlite3-dev libssl-dev llvm vim wget zlib1g-dev pip
    ```
6. Install pyenv:
    ```shell
    curl https://pyenv.run | bash
    ```
7. Configure your shell's environment for Pyenv:
    ```shell
    # the sed invocation inserts the lines at the start of the file
    # after any initial comment lines
    sed -Ei -e '/^([^#]|$)/ {a \
    export PYENV_ROOT="$HOME/.pyenv"
    a \
    export PATH="$PYENV_ROOT/bin:$PATH"
    a \
    ' -e ':a' -e '$!{n;ba};}' ~/.profile
    echo 'eval "$(pyenv init --path)"' >>~/.profile

    echo 'eval "$(pyenv init -)"' >> ~/.bashrc
    ```
8. Reload profile:
    ```shell
    source ~/.profile
    ```
9. Install Python:
    ```shell
    pyenv install 3.7.3
    ````
10. Enable the installed version.
    ```shell
    pyenv shell 3.7.3
    ```
11. Upgrade pip
    ```shell
    pip install --upgrade pip
    ```
12. Install the dependencies
    ```shell
    make install_deps
    make install_build_deps
    ```
13. Run the tests:
    ```shell
    make
    ```
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
