from codecs import open
from os import path
from textwrap import dedent

from setuptools import setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding='utf-8') as f:
    long_description = f.read()

# TODO: convert README from .md to .rst
setup(
    name='python-jsonstore',
    version='1.0.0',
    description="",
    long_description=long_description,
    author="Oliver Bristow",
    author_email='github+pypi@oliverbristow.co.uk',
    license='MIT',
    classifiers=dedent("""
        Development Status :: 5 - Production/Stable
        Intended Audience :: Developers
        Topic :: Database
        Topic :: Software Development
        License :: OSI Approved :: MIT License
        Programming Language :: Python :: 2
        Programming Language :: Python :: 2.7
        Programming Language :: Python :: 3
        Programming Language :: Python :: 3.3
        Programming Language :: Python :: 3.4
        Programming Language :: Python :: 3.5
        Programming Language :: Python :: 3.6
        Programming Language :: Python :: Implementation :: CPython
        Programming Language :: Python :: Implementation :: PyPy
    """).strip().split('\n'),
    keywords='json key value store',
    url='https://github.com/Code0x58/python-jsonstore/',
    py_modules=dedent("""
        jsonstore
        jsonstore.tests
    """).strip().split('\n'),
)
