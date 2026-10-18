#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
"""
Provides a Python class that maps values to/from a JSON file
"""
from __future__ import absolute_import
import json
import os
import stat
from collections import OrderedDict
from copy import deepcopy
from tempfile import mkstemp

__all__ = ["JsonStore"]

STRING_TYPES = (str,)
VALUE_TYPES = (bool, int, float, type(None))


class JsonStore(object):
    """A class to provide object based access to a JSON file"""

    def __enter__(self):
        current_state = self.__dict__["_data"]
        self.__dict__["_states"].append(current_state)
        self.__dict__["_data"] = deepcopy(current_state)
        return self

    def __exit__(self, *args):
        previous_state = self.__dict__["_states"].pop()
        if any(args):
            self.__dict__["_data"] = previous_state
        elif not self.__dict__["_states"]:
            try:
                self._save()
            except BaseException:
                self.__dict__["_data"] = previous_state
                raise

    def _do_auto_commit(self):
        if self._auto_commit and not self.__dict__["_states"]:
            self._save()

    def _load(self):
        if not os.path.exists(self._path):
            with open(self._path, "w+b") as store:
                store.write("{}".encode("utf-8"))
        with open(self._path, "r+b") as store:
            raw_data = store.read().decode("utf-8")
        if not raw_data:
            data = OrderedDict()
        else:
            data = json.loads(raw_data, object_pairs_hook=OrderedDict)

        if not isinstance(data, dict):
            raise ValueError("Root element is not an object")
        self.__dict__["_data"] = data

    def _save(self):
        output = json.dumps(self._data, indent=self._indent).encode("utf-8")
        try:
            mode = stat.S_IMODE(os.stat(self._path).st_mode)
        except FileNotFoundError:
            mode = None
        descriptor, temp = mkstemp(
            prefix="." + os.path.basename(self._path) + ".",
            suffix=".tmp",
            dir=os.path.dirname(os.path.abspath(self._path)),
        )
        try:
            with os.fdopen(descriptor, "wb") as store:
                store.write(output)
            if mode is not None:
                os.chmod(temp, mode)
            os.replace(temp, self._path)
        finally:
            try:
                os.unlink(temp)
            except FileNotFoundError:
                pass
            except PermissionError:
                if os.name != "nt":
                    raise
                os.chmod(temp, stat.S_IWRITE)
                os.unlink(temp)

    def __init__(self, path, indent=2, auto_commit=True):
        self.__dict__.update(
            {
                "_auto_commit": auto_commit,
                "_data": None,
                "_path": os.fsdecode(path),
                "_indent": indent,
                "_states": [],
            }
        )
        self._load()

    def __getattr__(self, key):
        if key in self._data:
            return deepcopy(self._data[key])
        else:
            raise AttributeError(key)

    @classmethod
    def _verify_object(cls, obj, parents=None):
        """
        Raise an exception if the object is not suitable for assignment.

        """
        if isinstance(obj, (dict, list)):
            if parents is None:
                parents = []
            elif any(o is obj for o in parents):
                raise ValueError("Cycle detected in list/dictionary")
            parents.append(obj)

        if isinstance(obj, dict):
            for k, v in obj.items():
                if not cls._valid_string(k):
                    # this is necessary because of the JSON serialisation
                    raise TypeError("a dict has non-string keys")
                cls._verify_object(v, parents)
        elif isinstance(obj, (list, tuple)):
            for o in obj:
                cls._verify_object(o, parents)
        else:
            if not cls._valid_value(obj):
                raise TypeError("unsupported JSON value type: %s" % type(obj).__name__)

    @classmethod
    def _valid_value(cls, value):
        if isinstance(value, VALUE_TYPES):
            return True
        else:
            return cls._valid_string(value)

    @classmethod
    def _valid_string(cls, value):
        if isinstance(value, STRING_TYPES):
            return True
        else:
            return False

    @classmethod
    def _canonical_key(cls, key):
        """Convert a set/get/del key into the canonical form."""
        if cls._valid_string(key):
            return tuple(key.split("."))

        if isinstance(key, (tuple, list)):
            key = tuple(key)
            if not key:
                raise TypeError("key must be a string or non-empty tuple/list")
            return key

        raise TypeError("key must be a string or non-empty tuple/list")

    def __setattr__(self, attr, value):
        self._verify_object(value)
        value = deepcopy(value)
        self._verify_object(value)
        self._data[attr] = value
        self._do_auto_commit()

    def __delattr__(self, attr):
        del self._data[attr]
        self._do_auto_commit()

    def __get_obj(self, steps):
        """Returns the object which is under the given path."""
        path = []
        obj = self._data
        for step in steps:
            if isinstance(obj, dict) and not self._valid_string(step):
                # this is necessary because of the JSON serialisation
                raise TypeError("%s is a dict and %s is not a string" % (path, step))
            try:
                obj = obj[step]
            except (KeyError, IndexError, TypeError) as e:
                raise type(e)("unable to get %s from %s: %s" % (step, path, e))
            path.append(step)
        return obj

    def __setitem__(self, key, value):
        steps = self._canonical_key(key)
        path, step = steps[:-1], steps[-1]
        self._verify_object(value)
        value = deepcopy(value)
        self._verify_object(value)
        container = self.__get_obj(path)
        if isinstance(container, dict) and not self._valid_string(step):
            raise TypeError("%s is a dict and %s is not a string" % (path, step))
        try:
            container[step] = value
        except (IndexError, TypeError) as e:
            raise type(e)("unable to set %s from %s: %s" % (step, path, e))
        self._do_auto_commit()

    def __getitem__(self, key):
        steps = self._canonical_key(key)
        obj = self.__get_obj(steps)
        return deepcopy(obj)

    def __delitem__(self, key):
        steps = self._canonical_key(key)
        path, step = steps[:-1], steps[-1]
        obj = self.__get_obj(path)
        try:
            del obj[step]
        except (KeyError, IndexError, TypeError) as e:
            raise type(e)("unable to delete %s from %s: %s" % (step, path, e))
        self._do_auto_commit()

    def __contains__(self, key):
        steps = self._canonical_key(key)
        try:
            self.__get_obj(steps)
            return True
        except (KeyError, IndexError, TypeError):
            # this is rather permissive as the types are dynamic
            return False
