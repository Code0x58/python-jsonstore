#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import os
import unittest
from jsonstore import JsonStore
from tempfile import mktemp


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
        self._db_file = mktemp()
        self.db = JsonStore(self._db_file)

    def tearDown(self):
        os.remove(self._db_file)

    def _setattr(self, key, value):
        """
        Return a callable that assigns self.db.key to value
        """
        def f():
            setattr(self.db, key, value)
        return f

    def _setitem(self, key, value):
        """
        Return a callable that assigns self.db[key] to value
        """
        def f():
            self.db[key] = value
        return f

    def _getattr(self, key):
        """
        Return a callable that assigns self.db.key to value
        """
        def f():
            return getattr(self.db, key)
        return f

    def _getitem(self, key):
        """
        Return a callable that assigns self.db[key] to value
        """
        def f():
            return self.db[key]
        return f

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

    def test_retrieve_values(self):
        for name, value in self.TEST_DATA:
            self.db[name] = value
            self.assertEqual(getattr(self.db, name), value)
            self.assertEqual(self.db[name], value)

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

        self.db.dictionary = {'a': 1}
        self.db['dictionary.exist'] = None
        self.assertIsNone(self.db.dictionary['exist'])
        self.assertIsNone(self.db['dictionary.exist'])

        self.db['dictionary.a'] = 2
        del self.db['dictionary.exist']
        self.assertRaises(KeyError, self._getitem('dictionary.exist'))
        self.assertNotIn('exist', self.db.dictionary)
        self.assertEqual(self.db.dictionary, {'a': 2})

    def test_del(self):
        self.db.key = None
        del self.db.key
        self.assertRaises(KeyError, self._getitem('key'))

        self.db.key = None
        del self.db['key']
        self.assertRaises(KeyError, self._getitem('key'))

    def test_context_and_deserialisation(self):
        db_file = mktemp()
        for name, value in self.TEST_DATA:
            if isinstance(value, tuple):
                value = list(value)
            with JsonStore(db_file) as db:
                db[name] = value
            with JsonStore(db_file) as db:
                self.assertEqual(getattr(db, name), value)


if __name__ == '__main__':
    unittest.main()
