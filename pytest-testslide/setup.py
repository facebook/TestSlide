# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os

from setuptools import setup

dir_path = os.path.dirname(os.path.realpath(__file__))

ts_version = open("testslide-version").read().rstrip()
requirements = open("requirements.txt", encoding="utf8").readlines()

with open("README.md", encoding="utf8") as f:
    readme = f.read()

setup(
    name="pytest-testslide",
    version=ts_version,
    py_modules=["pytest_testslide"],
    maintainer="Balint Csergo",
    maintainer_email="deathowlzz@gmail.com",
    url="https://github.com/facebook/TestSlide/tree/main/pytest-testslide",
    license="MIT",
    description="TestSlide fixture for pytest",
    long_description=readme,
    long_description_content_type="text/markdown",
    setup_requires=["setuptools>=38.6.0"],
    install_requires=[
        f"testslide>={ts_version}",
    ]
    + requirements,
    extras_require={"build": ["black", "flake8", "mypy"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Acceptance",
        "Topic :: Software Development :: Testing :: BDD",
        "Topic :: Software Development :: Testing :: Mocking",
        "Topic :: Software Development :: Testing :: Unit  ",
    ],
)
