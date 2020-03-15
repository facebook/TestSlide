# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from setuptools import setup

with open("README.md", encoding="utf8") as f:
    readme = f.read()

setup(
    name="pytest-testslide",
    version="1.0.0",
    py_modules=["pytest_testslide"],
    maintainer="Fabio Pugliese Ornellas",
    maintainer_email="fabio.ornellas@gmail.com",
    url="https://github.com/facebookincubator/TestSlide",
    license="MIT",
    description="TestSlide fixture for pytest",
    long_description=readme,
    long_description_content_type="text/markdown",
    setup_requires=["setuptools>=38.6.0"],
    install_requires=["testslide>=2.2.1", "pytest>=5.3.0",],
    extras_require={"build": ["black", "flake8",]},
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
    entry_points={"pytest11": ["pytest-testslide = pytest_testslide"]},
)
