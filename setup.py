import codecs
from os import path
from textwrap import dedent

from setuptools import setup

here = path.abspath(path.dirname(__file__))

with codecs.open(path.join(here, "README.rst"), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='python-jsonstore',
    use_scm_version=True,
    description="",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Oliver Bristow",
    author_email='github+pypi@oliverbristow.co.uk',
    license='MIT',
    classifiers=dedent("""
        Development Status :: 5 - Production/Stable
        Intended Audience :: Developers
        License :: OSI Approved :: MIT License
        Operating System :: OS Independent
        Programming Language :: Python :: 2
        Programming Language :: Python :: 2.7
        Programming Language :: Python :: 3
        Programming Language :: Python :: 3.3
        Programming Language :: Python :: 3.4
        Programming Language :: Python :: 3.5
        Programming Language :: Python :: 3.6
        Programming Language :: Python :: 3.7
        Programming Language :: Python :: Implementation :: CPython
        Programming Language :: Python :: Implementation :: PyPy
        Topic :: Database
        Topic :: Software Development
    """).strip().split('\n'),
    keywords='json key value store',
    url='https://github.com/Code0x58/python-jsonstore/',
    py_modules=dedent("""
        jsonstore
    """).strip().split('\n'),
    setup_requires=["setuptools_scm", "wheel"],
)
