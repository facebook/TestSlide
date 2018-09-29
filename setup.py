# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from distutils.core import setup
from io import open

setup(
    name="TestSlide",
    version="1.0.0.b1",
    packages=["testslide"],
    maintainer="Fabio Pugliese Ornellas",
    maintainer_email="fabio.ornellas@gmail.com",
    url="https://github.com/facebookincubator/TestSlide",
    license="MIT",
    description="A test framework for Python that makes mocking and iterating over code with tests a breeze",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "six",
        'typing;python_version<"3"',
        'mock;python_version<"3"',
        'black;python_version>"2"',
        "sphinx",
        "sphinx-autobuild",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Acceptance",
        "Topic :: Software Development :: Testing :: BDD",
        "Topic :: Software Development :: Testing :: Mocking",
        "Topic :: Software Development :: Testing :: Unit  ",
    ],
    entry_points={"console_scripts": ["testslide=testslide.cli:main"]},
)
