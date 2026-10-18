|PyPI| |Build Status| |Coverage Report| |Documentation|

jsonstore
=========

``JsonStore`` maps a JSON object's keys to Python attributes. Use it to
load and save configuration containing nested dictionaries and lists.

Requires Python 3.9 or newer. Tests run on CPython 3.9–3.15 and PyPy 3.11.

`Documentation <https://python-jsonstore.readthedocs.io/en/latest/>`__
includes the API reference and build instructions.

Examples
--------

Install with ``pip install python-jsonstore``.

Basics
~~~~~~

.. code:: python

    from jsonstore import JsonStore

    # Assignments and deletions are saved automatically.
    store = JsonStore("config.json")
    store.message = "hello"
    store.options = {"enabled": True, "greeting": "💐"}
    store.numbers = [1, 2, 3]
    assert "message" in store
    del store.message

    # Dot-separated keys traverse dictionaries.
    store["options.enabled"] = False
    assert store["options", "enabled"] is False

    # Tuple or list paths also accept list indices and slices.
    assert store["numbers", -1] == 3
    assert store[["numbers", 1]] == 2
    del store["numbers", :2]
    assert store.numbers == [3]

    # A one-element tuple addresses a literal key containing a dot.
    store[("literal.key",)] = "value"

Reads and assignments use deep copies. To update a stored collection,
assign the modified value back; ``+=`` also does this:

.. code:: python

    store.numbers.append(4)
    assert store.numbers == [3]
    store.numbers += [4, 5]
    assert store.numbers == [3, 4, 5]

Use item access for keys that conflict with ``JsonStore`` attributes.
``indent`` controls JSON formatting and defaults to 2; use ``None`` for
compact output. ``auto_commit=False`` defers saving until a transaction
commits.

Transactions
~~~~~~~~~~~~

Use ``with store:`` to group changes into a transaction. Transactions may
be nested; only successful exit from the outermost transaction saves the
file. An exception in a transaction restores its previous state, including
when saving fails.

.. code:: python

    from jsonstore import JsonStore

    with JsonStore("config.json", indent=None, auto_commit=False) as store:
        store.value = 1
    assert JsonStore("config.json").value == 1

    try:
        with store:
            store.value = 2
            with store:
                store.value = 3
            raise ValueError("cancel the transaction")
    except ValueError:
        pass
    assert store.value == 1
    assert JsonStore("config.json").value == 1

Transactions provide in-memory rollback, with no locking or coordination
between writers. Use one writer per file; separate stores do not reload
each other's changes. Atomic replacement does not guarantee durability
across a power failure.

.. |Build Status| image:: https://github.com/Code0x58/python-jsonstore/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/Code0x58/python-jsonstore/actions/workflows/ci.yml
.. |PyPI| image:: https://img.shields.io/pypi/v/python-jsonstore.svg
   :target: https://pypi.org/project/python-jsonstore/
.. |Coverage Report| image:: https://codecov.io/gh/Code0x58/python-jsonstore/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/Code0x58/python-jsonstore
.. |Documentation| image:: https://readthedocs.org/projects/python-jsonstore/badge/?version=latest
   :target: https://python-jsonstore.readthedocs.io/en/latest/
   :alt: Documentation status
