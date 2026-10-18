#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import

import json
import os
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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
        self._directory = TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self._store_file = os.path.join(self._directory.name, "store.json")
        self.store = JsonStore(self._store_file, indent=None, auto_commit=True)

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
        store_file = os.path.join(self._directory.name, "new-store.json")
        JsonStore(store_file, auto_commit=True)
        with open(store_file) as handle:
            self.assertEqual(handle.read(), "{}")
        os.remove(store_file)

        JsonStore(store_file, auto_commit=False)
        with open(store_file) as handle:
            self.assertEqual(handle.read(), "{}")
        os.remove(store_file)

    def test_assign_valid_types(self):
        for name, value in self.TEST_DATA:
            self.store[name] = value
            self.assertEqual(self.store[name], value)
            self.assertEqual(getattr(self.store, name), value)

            del self.store[name]
            self.assertRaises(KeyError, self._getitem(name))
            self.assertRaises(AttributeError, self._getattr(name))

            setattr(self.store, name, value)
            self.assertEqual(self.store[name], value)
            self.assertEqual(getattr(self.store, name), value)

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

    def test_invalid_values_leave_store_unchanged(self):
        values = (object(), set(), b"bytes", {"nested": object()},
                  [1, {"nested": set()}], (1, object()), {1: "non-string key"})
        for auto_commit in (False, True):
            for method in ("attribute", "item", "nested item", "slice"):
                for value in values:
                    with self.subTest(auto_commit=auto_commit, method=method,
                                      value_type=type(value).__name__):
                        self.store.value = "original"
                        self.store.nested = {"key": "original"}
                        self.store.items = [1, 2]
                        store = JsonStore(self._store_file, auto_commit=auto_commit)
                        before = Path(self._store_file).read_bytes()
                        with self.assertRaises(TypeError):
                            if method == "attribute":
                                store.value = value
                            elif method == "item":
                                store["value"] = value
                            elif method == "nested item":
                                store["nested.key"] = value
                            else:
                                store["items", :] = value
                        self.assertEqual(store.value, "original")
                        self.assertEqual(store.nested, {"key": "original"})
                        self.assertEqual(store.items, [1, 2])
                        self.assertEqual(Path(self._store_file).read_bytes(), before)
                        with store:
                            store.good = 1
                        self.assertEqual(JsonStore(self._store_file).good, 1)

    def test_invalid_value_cannot_poison_new_key(self):
        for auto_commit in (False, True):
            for assign in (setattr, lambda store, key, value: store.__setitem__(key, value)):
                with self.subTest(auto_commit=auto_commit, assign=assign):
                    store = JsonStore(self._store_file, auto_commit=auto_commit)
                    with self.assertRaises(TypeError):
                        assign(store, "bad", object())
                    self.assertNotIn("bad", store)
                    with store:
                        store.good = 1
                    self.assertEqual(JsonStore(self._store_file).good, 1)

    def test_deepcopy_result_is_validated_before_assignment(self):
        class InvalidCopy(str):
            def __deepcopy__(self, memo):
                return object()

        class InvalidValue:
            def __deepcopy__(self, memo):
                return "valid-looking copy"

        for assign in (setattr, lambda store, key, value: store.__setitem__(key, value)):
            for value in (InvalidCopy("value"), InvalidValue()):
                with self.subTest(assign=assign, value_type=type(value).__name__):
                    with self.assertRaises(TypeError):
                        assign(self.store, "bad", value)
                    self.assertNotIn("bad", self.store)

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
        store_file = os.path.join(self._directory.name, "empty.json")
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

    def test_deletions_are_auto_committed(self):
        cases = (
            (lambda store: delattr(store, "value"), {}),
            (lambda store: store.__delitem__("value"), {}),
            (lambda store: store.__delitem__("value.key"),
             {"value": {"items": [1, 2, 3]}}),
            (lambda store: store.__delitem__(("value", "items", 1)),
             {"value": {"key": 1, "items": [1, 3]}}),
            (lambda store: store.__delitem__(("value", "items", slice(0, 2))),
             {"value": {"key": 1, "items": [3]}}),
        )
        for index, (delete, expected) in enumerate(cases):
            with self.subTest(case=index):
                self.store.value = {"key": 1, "items": [1, 2, 3]}
                delete(self.store)
                with open(self._store_file) as handle:
                    self.assertEqual(json.load(handle), expected)
                self.assertEqual(JsonStore(self._store_file)._data, expected)

    def test_deletion_respects_deferred_commits(self):
        self.store.key = 1
        with self.store:
            del self.store.key
            self.assertEqual(JsonStore(self._store_file).key, 1)
        self.assertNotIn("key", JsonStore(self._store_file))

        self.store.key = 1
        store = JsonStore(self._store_file, auto_commit=False)
        del store["key"]
        self.assertNotIn("key", store)
        self.assertEqual(JsonStore(self._store_file).key, 1)

    def test_context_and_deserialisation(self):
        store_file = os.path.join(self._directory.name, "roundtrip.json")
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
        store_file = os.path.join(self._directory.name, "auto-commit.json")
        store = JsonStore(store_file, indent=None, auto_commit=True)
        store.value1 = 1
        with open(store_file) as handle:
            self.assertEqual({"value1": 1}, json.load(handle))
        store["value2"] = 2
        with open(store_file) as handle:
            self.assertEqual({"value1": 1, "value2": 2}, json.load(handle))

    def test_no_auto_commit(self):
        store_file = os.path.join(self._directory.name, "no-auto-commit.json")
        store = JsonStore(store_file, indent=None, auto_commit=False)
        store.value1 = 1
        store["value2"] = 2
        with open(store_file) as handle:
            self.assertEqual({}, json.load(handle))

    def test_save_preserves_unrelated_backup(self):
        backup = Path(self._store_file + "~")
        backup.write_text("unrelated backup", encoding="utf-8")
        self.store.value = 1
        self.assertEqual(backup.read_text(encoding="utf-8"), "unrelated backup")
        self.assertEqual(JsonStore(self._store_file).value, 1)

    @unittest.skipIf(os.name == "nt", "Creating symlinks requires Windows privileges")
    def test_save_does_not_follow_backup_symlink(self):
        unrelated = Path(self._directory.name, "unrelated.txt")
        unrelated.write_text("unrelated content", encoding="utf-8")
        backup = Path(self._store_file + "~")
        backup.symlink_to(unrelated)
        self.store.value = 1
        self.assertTrue(backup.is_symlink())
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "unrelated content")

    def test_overlapping_saves_use_separate_temporary_files(self):
        first = JsonStore(self._store_file, auto_commit=False)
        second = JsonStore(self._store_file, auto_commit=False)
        first.value = "first writer"
        second.value = "second writer"
        replace = os.replace
        sources = []

        def interleave(source, destination):
            sources.append(source)
            if len(sources) == 1:
                second._save()
                self.assertEqual(JsonStore(self._store_file).value, "second writer")
            replace(source, destination)

        with patch("jsonstore.os.replace", side_effect=interleave):
            first._save()
        self.assertEqual(len(set(sources)), 2)
        self.assertEqual(JsonStore(self._store_file).value, "first writer")

    def test_failed_replacement_removes_temporary_file(self):
        before = set(os.listdir(self._directory.name))
        with patch("jsonstore.os.replace", side_effect=OSError("replacement failed")):
            with self.assertRaises(OSError):
                self.store.value = 1
        self.assertEqual(set(os.listdir(self._directory.name)), before)
        self.assertNotIn("value", JsonStore(self._store_file))

    def test_pathlike_store_can_be_saved(self):
        store = JsonStore(Path(self._store_file))
        store.value = 1
        self.assertEqual(JsonStore(self._store_file).value, 1)

    @unittest.skipIf(os.name == "nt", "POSIX permission bits are not supported on Windows")
    def test_save_preserves_file_permissions(self):
        for mode in (0o600, 0o640, 0o660):
            with self.subTest(mode=oct(mode)):
                os.chmod(self._store_file, mode)
                self.store.value = mode
                self.assertEqual(stat.S_IMODE(os.stat(self._store_file).st_mode), mode)
                self.assertEqual(JsonStore(self._store_file).value, mode)

    def test_save_recreates_removed_file(self):
        os.unlink(self._store_file)
        self.store.value = 1
        self.assertEqual(JsonStore(self._store_file).value, 1)

    def test_failed_replacement_cleans_up_readonly_temporary_file(self):
        before = set(os.listdir(self._directory.name))
        try:
            os.chmod(self._store_file, stat.S_IREAD)
            with patch("jsonstore.os.replace", side_effect=OSError("replacement failed")):
                with self.assertRaisesRegex(OSError, "replacement failed"):
                    self.store.value = 1
            self.assertEqual(set(os.listdir(self._directory.name)), before)
        finally:
            os.chmod(self._store_file, stat.S_IREAD | stat.S_IWRITE)

    @unittest.skipIf(os.name == "nt" or os.geteuid() == 0,
                     "Requires POSIX directory permissions without root privileges")
    def test_cleanup_permission_failure_is_propagated(self):
        def lose_directory_write_permission(source, destination):
            os.chmod(self._directory.name, 0o500)
            raise OSError("replacement failed")

        try:
            with patch("jsonstore.os.replace", side_effect=lose_directory_write_permission):
                with self.assertRaises(PermissionError):
                    self.store.value = 1
            self.assertNotIn("value", JsonStore(self._store_file))
        finally:
            os.chmod(self._directory.name, 0o700)

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

    def test_failed_transaction_commit_restores_state(self):
        self.store.value = {"items": [1]}
        for auto_commit in (False, True):
            with self.subTest(auto_commit=auto_commit):
                store = JsonStore(self._store_file, auto_commit=auto_commit)
                with patch("jsonstore.os.replace", side_effect=OSError("commit failed")):
                    with self.assertRaisesRegex(OSError, "commit failed"):
                        with store:
                            store["value", "items", 0] = 2
                            with store:
                                store.extra = 3
                self.assertEqual(store.value, {"items": [1]})
                self.assertNotIn("extra", store)
                self.assertEqual(JsonStore(self._store_file).value, {"items": [1]})
                self.assertNotIn("extra", JsonStore(self._store_file))
                self.assertEqual(store._states, [])

                with store:
                    store.value = {"items": [4]}
                self.assertEqual(JsonStore(self._store_file).value, {"items": [4]})
                self.store.value = {"items": [1]}

    def test_interrupted_transaction_commit_restores_state(self):
        self.store.value = 1
        with patch.object(JsonStore, "_save", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                with self.store:
                    self.store.value = 2
        self.assertEqual(self.store.value, 1)
        self.assertEqual(JsonStore(self._store_file).value, 1)
        self.assertEqual(self.store._states, [])

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
