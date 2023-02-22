# -*- coding: utf-8 -*-

# Copyright (c) 2019-2021 BigHat Biosciences.  All rights reserved.  Do not use, copy, or disclose to
# others without prior written permission.

from setuptools import setup, find_namespace_packages

with open("VERSION", "r", encoding="utf8") as ver_file:
    VERSION = ver_file.read().strip()

REQUIRES = ["aiofiles", "biopython", "fastapi", "numpy", "pandas", "pydantic", "python-multipart", "uvicorn"]

setup(
    author="BigHat Biosciences",
    author_email="whaynes@bighatbio.com",
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Utilities",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    description="BigHat fork of nanobody-polyreactivity to expose backend as a package",
    include_package_data=True,
    install_requires=REQUIRES,
    keywords="example",
    long_description="",
    name="bh-polyreactivity",  # this is the 'requires' name
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    setup_requires="",
    tests_requires="",
    url="https://github.com/BigHat-Biosciences/nanobody-polyreactivity/",
    version=VERSION,
    zip_safe=False,
)
