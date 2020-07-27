# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from setuptools import setup

version = open("testslide/version").read().rstrip()
readme = open("README.md", encoding="utf8").read()

setup(
    name="TestSlide",
    version=version,
    packages=["testslide"],
    maintainer="Fabio Pugliese Ornellas",
    maintainer_email="fabio.ornellas@gmail.com",
    url="https://github.com/facebookincubator/TestSlide",
    license="MIT",
    description="A test framework for Python that makes mocking and iterating over code with tests a breeze",
    long_description=readme,
    long_description_content_type="text/markdown",
    setup_requires=["setuptools>=38.6.0"],
    install_requires=["psutil>=5.6.7", "typeguard>=2.9.1",],
    extras_require={
        "build": [
            "black",
            "coverage",
            "coveralls",
            "flake8",
            "isort~=5.1",
            "mypy",
            "ipython",
            "sphinx",
            "sphinx-autobuild",
            "sphinx_rtd_theme",
            "twine",
        ]
    },
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
    entry_points={"console_scripts": ["testslide=testslide.cli:main"]},
)
