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
        ("string", "hello"),
        ("unicode", u"💩"),
        ("integer", 1),
        ("none", None),
        ("big_integer", 18446744073709551616),
        ("float", 1.0),
        ("boolean", True),
        ("list", [1, 2]),
        ("tuple", (1, 2)),
        ("dictionary", {"key": "value"}),
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

        def handle():
            setattr(self.store, key, value)

        return handle

    def _setitem(self, key, value):
        """
        Return a callable that assigns self.store[key] to value
        """

        def handle():
            self.store[key] = value

        return handle

    def _getattr(self, key):
        """
        Return a callable that assigns self.store.key to value
        """

        def handle():
            return getattr(self.store, key)

        return handle

    def _getitem(self, key):
        """
        Return a callable that assigns self.store[key] to value
        """

        def handle():
            return self.store[key]

        return handle

    def test_new_store(self):
        store_file = mktemp()
        JsonStore(store_file, auto_commit=True)
        with open(self._store_file) as handle:
            self.assertEqual(handle.read(), "{}")
        os.remove(store_file)

        JsonStore(store_file, auto_commit=False)
        with open(self._store_file) as handle:
            self.assertEqual(handle.read(), "{}")
        os.remove(store_file)

    def test_assign_valid_types(self):
        for name, value in self.TEST_DATA:
            self.store[name] = value
            self.store[name] == value
            getattr(self.store, name) == value

            del self.store[name]
            self.assertRaises(KeyError, self._getitem(name))
            self.assertRaises(AttributeError, self._getattr(name))

            setattr(self.store, name, value)
            self.store[name] == value
            getattr(self.store, name) == value

            delattr(self.store, name)
            self.assertRaises(KeyError, self._getitem(name))
            self.assertRaises(AttributeError, self._getattr(name))

    def test_slices(self):
        self.store.list = [1, 2, 3]
        self.store["list", :2] = ["a", "b"]
        self.assertEqual(self.store["list", 1:], ["b", 3])
        del self.store["list", :1]
        self.assertEqual(self.store.list, ["b", 3])

    def test_assign_invalid_types(self):
        for method in (self._setattr, self._setitem):

            def assign(value):
                return method("key", value)

            self.assertRaises(TypeError, assign(set()))
            self.assertRaises(TypeError, assign(object()))
            self.assertRaises(TypeError, assign(None for i in range(2)))
            self.assertRaises(TypeError, assign({1: 1}))

    def test_assign_bad_keys(self):
        value = 1
        # the root object is a dict, so a string key is needed
        self.assertRaises(TypeError, self._setitem(1, value))
        self.assertRaises(TypeError, self._setitem((1, "a"), value))

        self.store["dict"] = {}
        self.store["list"] = []
        self.assertRaises(TypeError, self._setitem((), value))
        self.assertRaises(TypeError, self._setitem(("dict", 1), value))
        self.assertRaises(TypeError, self._setitem(("dict", slice(1)), value))
        self.assertRaises(TypeError, self._setitem(("list", "a"), value))
        self.assertRaises(TypeError, self._setitem(("list", slice("a")), value))
        self.assertRaises(IndexError, self._setitem(("list", 1), value))


    def test_retrieve_values(self):
        for name, value in self.TEST_DATA:
            self.store[name] = value
            self.assertEqual(getattr(self.store, name), value)
            self.assertEqual(self.store[name], value)

    def test_has_values(self):
        for name, value in self.TEST_DATA:
            self.store[name] = value
            self.assertTrue(name in self.store)

        self.assertFalse("foo" in self.store)

    def test_empty_key(self):
        with self.assertRaises(KeyError):
            return self.store[""]

    def test_empty_store(self):
        store_file = mktemp()
        with open(store_file, "wb") as f:
            f.write(b"")
        self.assertTrue(JsonStore(f.name))

    def test_assign_cycle(self):
        test_list = []
        test_dict = {}
        test_list.append(test_dict)
        test_dict["list"] = test_list
        for method in (self._setattr, self._setitem):
            self.assertRaises(ValueError, method("key", test_list))
            self.assertRaises(ValueError, method("key", test_dict))

    def test_nested_dict_helper(self):
        self.assertRaises(KeyError, self._setitem("dictionary.noexist", None))
        self.assertRaises(KeyError, self._getitem("dictionary.noexist"))

        for access_key in ("dictionary.exist", ("dictionary", "exist"), ["dictionary", "exist"]):
            self.store.dictionary = {"a": 1}
            self.store["dictionary.exist"] = None
            self.assertIsNone(self.store.dictionary["exist"])
            self.assertIsNone(self.store[access_key])

            self.store["dictionary.a"] = 2
            del self.store[access_key]
            self.assertRaises(KeyError, self._getitem(access_key))
            self.assertNotIn("exist", self.store.dictionary)
            self.assertEqual(self.store.dictionary, {"a": 2})

    def test_nested_getitem(self):
        self.store["list"] = [
            {
                "key": [None, "value", "last"]
            }
        ]
        assert self.store["list", 0, "key", 1] == "value"
        assert self.store[["list", 0, "key", -1]] == "last"
        self.assertRaises(TypeError, self._getitem("list.0.key.1"))
        assert len(self.store["list", 0, "key", 1:]) == 2
        self.assertRaises(IndexError, self._getitem(("list", 1)))

    def test_del(self):
        self.store.key = None
        del self.store.key
        self.assertRaises(KeyError, self._getitem("key"))

        self.store.key = None
        del self.store["key"]
        self.assertRaises(KeyError, self._getitem("key"))

        with self.assertRaises(KeyError):
            del self.store["missing"]

        self.store.list = []
        with self.assertRaises(IndexError):
            del self.store["list", 1]

        self.store.dict = {}
        # somewhere after python 3.9 this went from a TypeError to a KeyError
        with self.assertRaises((TypeError, KeyError)):
            del self.store["dict", slice("a")]

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
        outer_dict = {"key": inner_dict}

        for method in (self._getattr, self._getitem):
            self.store.list = outer_list
            self.assertIsNot(method("list")(), outer_list)
            self.assertIsNot(method("list")()[0], inner_list)

            self.store.dict = outer_dict
            self.assertIsNot(method("dict")(), outer_dict)
            self.assertIsNot(method("dict")()["key"], inner_dict)

            self.assertIsNot(method("list")(), method("list")())
            self.assertIsNot(method("list")()[0], method("list")()[0])
            self.assertIsNot(method("dict")(), method("dict")())
            self.assertIsNot(method("dict")()["key"], method("dict")()["key"])

    def test_load(self):
        for good_data in ("{}", '{"key": "value"}'):
            with open(self._store_file, "w") as handle:
                handle.write(good_data)
            self.store._load()

        for bad_data in ("[]", "1", "nill", '"x"'):
            with open(self._store_file, "w") as handle:
                handle.write(bad_data)
            self.assertRaises(ValueError, self.store._load)

    def test_auto_commit(self):
        store_file = mktemp()
        store = JsonStore(store_file, indent=None, auto_commit=True)
        store.value1 = 1
        with open(store_file) as handle:
            self.assertEqual({"value1": 1}, json.load(handle))
        store["value2"] = 2
        with open(store_file) as handle:
            self.assertEqual({"value1": 1, "value2": 2}, json.load(handle))

    def test_no_auto_commit(self):
        store_file = mktemp()
        store = JsonStore(store_file, indent=None, auto_commit=False)
        store.value1 = 1
        store["value2"] = 2
        with open(store_file) as handle:
            self.assertEqual({}, json.load(handle))

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
        self.assertRaises(AttributeError, self._getattr("remove_me"))

    def test_transaction_write(self):
        with self.store:
            self.store.value1 = 1
            with open(self._store_file) as handle:
                self.assertEqual(handle.read(), "{}")
            with self.store:
                self.store.value2 = 2
            with open(self._store_file) as handle:
                self.assertEqual(handle.read(), "{}")
        with open(self._store_file) as handle:
            self.assertEqual(handle.read(), '{"value1": 1, "value2": 2}')

    def test_list_concat_inplace(self):
        self.store.list = []
        extension = [{"key": "value"}]

        # make sure += happens
        self.store["list"] += extension
        self.store.list += extension
        self.assertEqual(self.store.list, extension * 2)

        # make sure a deepcopy occurred
        self.assertIsNot(self.store.list[0], extension[0])


if __name__ == "__main__":
    unittest.main()
