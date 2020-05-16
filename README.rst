|PyPi Package| |Build Status| |Codacy Rating| |Coverage Report|

jsonstore
=========

This module provides a class that maps keys and values from a JSON file
onto its attributes.

The goal was to provide a convenient way of loading and saving
configuration in a familiar human readable format. This is a bit more
flexible than the
`configparser <https://docs.python.org/3/library/configparser.html>`__
module which is included with Python.

This works is tested and working on Python 2.7+ and Python 3.3+. It will
not work on 2.6 or lower, but is expected to work on 3.0-3.2. The tests
do not work in 3.2.6 due to
`mistreating <https://travis-ci.org/Code0x58/python-jsonstore/jobs/198150401>`__
the 💩 when parsing the test code. This is also tested on pypy and pypy3.

Examples
--------

Basics
~~~~~~

.. code:: python

    # by default JsonStore commits on every change unless in a transaction
    store = JsonStore('config.json')
    store.a_string = "something"
    store.a_list = [1, 2, 3]
    store.a_dictionary = {
      'dict-list': [{}],
      'ln(2)': 0.69314718056,
      'for-you': u"💐",
    }

    # you can use […] to set/get/delete string keys
    store['some_key'] = "a value"
    # the key is split on '.'s and works on dictionaries
    del store['a_dictionary.dict-list']
    store['a_dictionary.new_value'] = "old value"
    #  you can also use the syntactic sugar for tuple keys (explicit lists work too)
    assert store['a_dictionary', 'new_value'] == "old value"
    # you can traverse lists too
    assert store['a_list', -1] == 3
    # you can use slices in lists
    assert len(store['a_list', 1:]) == 2
    del store['a_list', :2]
    assert store.a_list == [3]

    # deep copies are made when assigning values
    my_list = ['fun']
    store.a_list = my_list
    assert store.a_list is not my_list
    assert 'a_list' in store

    # deep copies are also returned to avoid unsanitary changes being made
    store.a_dictionary['new_value'] = "new value"  # won't update the store!
    assert store.a_dictionary['new_value'] == "old value"
    assert store.a_dictionary is not store.a_dictionary

Transactions
~~~~~~~~~~~~

``JsonStore`` objects can be used as `context
managers <https://www.python.org/dev/peps/pep-0343/>`__ to provide
transactions which are rolled back in the event of an exception. The
transaction model is primitive; you can only nest transactions.

While a store is put into a transaction, it will not save changes to
file until all of the transactions have been closed.

.. code:: python

    from jsonstore import JsonStore

    # even with auto_commit=True, the file won't be saved until the last contexts has been closed
    with JsonStore('config.json', indent=None, auto_commit=False) as store:
      self.value = 1

    # the context manager will roll back changes made if an exception is raised
    store = JsonStore('config.json', indent=None)
    try:
      with store:
        store.value = "new"
        raise Exception
    except Exception:
      pass
    # here we see the value that was saved previously
    assert store.value == 1

.. |Build Status| image:: https://travis-ci.org/Code0x58/python-jsonstore.svg?branch=master
   :target: https://travis-ci.org/Code0x58/python-jsonstore
.. |Codacy Rating| image:: https://api.codacy.com/project/badge/Grade/37ea488773444de59469a3775be83faf
   :target: https://www.codacy.com/app/evilumbrella-github/python-jsonstore?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Code0x58/python-jsonstore&amp;utm_campaign=Badge_Grade
.. |PyPi Package| image:: https://badge.fury.io/py/python-jsonstore.svg
   :target: https://pypi.org/project/python-jsonstore/
.. |Coverage Report| image:: https://codecov.io/gh/Code0x58/python-jsonstore/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/Code0x58/python-jsonstore