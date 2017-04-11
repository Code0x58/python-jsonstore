#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import json
import os
import unittest
from tempfile import mktemp

from jsonstore import JsonStore


class TransactionBreaker(Exception):
    pass


class Tests(unittest.TestCase):
    TEST_DATA = (
        ('string', "hello"),
        ('unicode', u"💩"),
        ('integer', 1),
        ('none', None),
        ('big_integer', 18446744073709551616),
        ('float', 1.0),
        ('boolean', True),
        ('list', [1, 2]),
        ('tuple', (1, 2)),
        ('dictionary', {'key': "value"}),
    )

    def setUp(self):
        self._store_file = mktemp()
        self.store = JsonStore(self._store_file, indent=None, auto_commit=True)

    def tearDown(self):
        os.remove(self._store_file)

    def _setattr(self, key, value):
        """
        Return a callable that assigns self.store.key to value
        """
        def f():
            setattr(self.store, key, value)
        return f

    def _setitem(self, key, value):
        """
        Return a callable that assigns self.store[key] to value
        """
        def f():
            self.store[key] = value
        return f

    def _getattr(self, key):
        """
        Return a callable that assigns self.store.key to value
        """
        def f():
            return getattr(self.store, key)
        return f

    def _getitem(self, key):
        """
        Return a callable that assigns self.store[key] to value
        """
        def f():
            return self.store[key]
        return f

    def test_new_store(self):
        store_file = mktemp()
        JsonStore(store_file, auto_commit=True)
        with open(self._store_file) as f:
            self.assertEqual(f.read(), '{}')
        os.remove(store_file)

        JsonStore(store_file, auto_commit=False)
        with open(self._store_file) as f:
            self.assertEqual(f.read(), '{}')
        os.remove(store_file)

    def test_assign_valid_types(self):
        for method in (self._setattr, self._setitem):
            for name, value in self.TEST_DATA:
                method(name, value)

    def test_assign_invalid_types(self):
        for method in (self._setattr, self._setitem):
            def assign(value):
                return method('key', value)
            self.assertRaises(AttributeError, assign(set()))
            self.assertRaises(AttributeError, assign(object()))
            self.assertRaises(AttributeError, assign(None for i in range(2)))

    def test_assign_bad_keys(self):
        # FIXME: a ValueError would make more sense
        self.assertRaises(AttributeError, self._setitem(1, 2))

    def test_retrieve_values(self):
        for name, value in self.TEST_DATA:
            self.store[name] = value
            self.assertEqual(getattr(self.store, name), value)
            self.assertEqual(self.store[name], value)

    def test_assign_cycle(self):
        test_list = []
        test_dict = {}
        test_list.append(test_dict)
        test_dict['list'] = test_list
        for method in (self._setattr, self._setitem):
            self.assertRaises(ValueError, method('key', test_list))
            self.assertRaises(ValueError, method('key', test_dict))

    def test_nested_dict_helper(self):
        self.assertRaises(KeyError, self._setitem('dictionary.noexist', None))
        self.assertRaises(KeyError, self._getitem('dictionary.noexist'))

        self.store.dictionary = {'a': 1}
        self.store['dictionary.exist'] = None
        self.assertIsNone(self.store.dictionary['exist'])
        self.assertIsNone(self.store['dictionary.exist'])

        self.store['dictionary.a'] = 2
        del self.store['dictionary.exist']
        self.assertRaises(KeyError, self._getitem('dictionary.exist'))
        self.assertNotIn('exist', self.store.dictionary)
        self.assertEqual(self.store.dictionary, {'a': 2})

    def test_del(self):
        self.store.key = None
        del self.store.key
        self.assertRaises(KeyError, self._getitem('key'))

        self.store.key = None
        del self.store['key']
        self.assertRaises(KeyError, self._getitem('key'))

    def test_context_and_deserialisation(self):
        store_file = mktemp()
        for name, value in self.TEST_DATA:
            if isinstance(value, tuple):
                value = list(value)
            with JsonStore(store_file) as store:
                store[name] = value
            with JsonStore(store_file) as store:
                self.assertEqual(getattr(store, name), value)

    def test_deep_copying(self):
        inner_list = []
        outer_list = [inner_list]
        inner_dict = {}
        outer_dict = {'key': inner_dict}

        for method in (self._getattr, self._getitem):
            self.store.list = outer_list
            self.assertIsNot(method('list')(), outer_list)
            self.assertIsNot(method('list')()[0], inner_list)

            self.store.dict = outer_dict
            self.assertIsNot(method('dict')(), outer_dict)
            self.assertIsNot(method('dict')()['key'], inner_dict)

            self.assertIsNot(method('list')(), method('list')())
            self.assertIsNot(method('list')()[0], method('list')()[0])
            self.assertIsNot(method('dict')(), method('dict')())
            self.assertIsNot(method('dict')()['key'], method('dict')()['key'])

    def test_load(self):
        for good_data in ("{}", '{"key": "value"}'):
            with open(self._store_file, 'w') as f:
                f.write(good_data)
            self.store._load()

        for bad_data in ('[]', '1', 'nill', '"x"'):
            with open(self._store_file, 'w') as f:
                f.write(bad_data)
            self.assertRaises(ValueError, self.store._load)

    def test_auto_commit(self):
        store_file = mktemp()
        store = JsonStore(store_file, indent=None, auto_commit=True)
        store.value1 = 1
        with open(store_file) as f:
            self.assertEqual(
                {'value1': 1},
                json.load(f),
                )
        store['value2'] = 2
        with open(store_file) as f:
            self.assertEqual(
                {'value1': 1, 'value2': 2},
                json.load(f),
                )

    def test_no_auto_commit(self):
        store_file = mktemp()
        store = JsonStore(store_file, indent=None, auto_commit=False)
        store.value1 = 1
        store['value2'] = 2
        with open(store_file) as f:
            self.assertEqual({}, json.load(f))

    def test_transaction_rollback(self):
        self.store.value = 1
        try:
            with self.store:
                self.store.value = 2
                try:
                    with self.store:
                        self.store.value = 3
                        raise TransactionBreaker
                except TransactionBreaker:
                    pass
                self.assertEqual(self.store.value, 2)
                raise TransactionBreaker
        except TransactionBreaker:
            pass
        self.assertEqual(self.store.value, 1)

    def test_transaction_commit(self):
        self.store.value = 1
        self.store.remove_me = "bye"
        with self.store:
            self.store.value = 2
            del self.store.remove_me
        self.assertEqual(self.store.value, 2)
        self.assertRaises(KeyError, self._getattr('remove_me'))

    def test_transaction_write(self):
        with self.store:
            self.store.value1 = 1
            with open(self._store_file) as f:
                self.assertEqual(f.read(), '{}')
            with self.store:
                self.store.value2 = 2
            with open(self._store_file) as f:
                self.assertEqual(f.read(), '{}')
        with open(self._store_file) as f:
            self.assertEqual(f.read(), '{"value1": 1, "value2": 2}')


if __name__ == '__main__':
    unittest.main()
