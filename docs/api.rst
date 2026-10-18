API Reference
=============

.. autoclass:: jsonstore.JsonStore

   :param path: Path to a JSON file, as a string or :class:`os.PathLike`.
      A missing file is created as an empty JSON object. Its parent directory
      must already exist.
   :param indent: Indentation passed to :func:`json.dumps`; defaults to 2.
      Use ``None`` for compact output.
   :param bool auto_commit: Save after each assignment or deletion, unless
      inside a transaction. Defaults to ``True``. With ``False``, use a
      context manager to commit changes.
   :raises ValueError: The file contains invalid JSON or its root is not an
      object. An empty file is treated as an empty object.
   :raises OSError: The file cannot be read or created.

Keys and values
---------------

Use attribute access for ordinary top-level keys. Item access also supports
dot-separated dictionary paths and tuple or list paths containing dictionary
keys, list indices, and slices. A one-element tuple addresses a literal key
containing a dot. Dictionary keys must be strings.

Values may be strings, booleans, integers, floats, ``None``, dictionaries,
lists, or tuples containing these types. Tuples are saved as JSON arrays and
become lists when the file is reopened. Non-finite floats use Python's JSON
extensions and are not portable to strict JSON readers.

Reads and assignments use deep copies. Assign a changed collection back to
the store to persist it. Unsupported values and non-string dictionary keys
raise :class:`TypeError`; reference cycles raise :class:`ValueError`.
Shared containers without cycles are accepted.

Transactions and saving
-----------------------

``with store:`` defers writes until the outermost transaction exits
successfully, regardless of ``auto_commit``. Exceptions restore the previous
state, including when the commit fails. Nested transactions provide nested
rollback scopes.

Saves use a unique temporary file beside the destination, preserve existing
permission bits, and atomically replace the destination. The containing
directory must be writable. This does not provide locking, coordination
between writers, or durability across power failures. Use one writer per file;
separate stores retain their own snapshots.
