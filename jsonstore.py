#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
"""
Provides a Python class that maps values to/from a JSON file
"""
from __future__ import absolute_import
import json
import os.path
import sys
from collections import OrderedDict
from copy import deepcopy

__all__ = ["JsonStore"]


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
            self._save()

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
        temp = self._path + "~"
        with open(temp, "wb") as store:
            output = json.dumps(self._data, indent=self._indent)
            store.write(output.encode("utf-8"))
        
        if sys.version_info >= (3, 3):
            os.replace(temp, self._path)
        elif os.name == "windows":
            os.remove(self._path)
            os.rename(temp, self._path)
        else:
            os.rename(temp, self._path)

    def __init__(self, path, indent=2, auto_commit=True):
        self.__dict__.update(
            {
                "_auto_commit": auto_commit,
                "_data": None,
                "_path": path,
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
    def _valid_object(cls, obj, parents=None):
        """
        Determine if the object can be encoded into JSON
        """
        # pylint: disable=unicode-builtin,long-builtin
        if isinstance(obj, (dict, list)):
            if parents is None:
                parents = []
            elif any(o is obj for o in parents):
                raise ValueError("Cycle detected in list/dictionary")
            parents.append(obj)

        if isinstance(obj, dict):
            return all(
                cls._valid_string(k) and cls._valid_object(v, parents)
                for k, v in obj.items()
            )
        elif isinstance(obj, (list, tuple)):
            return all(cls._valid_object(o, parents) for o in obj)
        else:
            return cls._valid_value(obj)

    @classmethod
    def _valid_value(cls, value):
        if isinstance(value, (bool, int, float, type(None))):
            return True
        elif sys.version_info < (3,) and isinstance(value, long):
            return True
        else:
            return cls._valid_string(value)

    @classmethod
    def _valid_string(cls, value):
        if isinstance(value, str):
            return True
        elif sys.version_info < (3,):
            return isinstance(value, unicode)
        else:
            return False

    def __setattr__(self, key, value):
        if not self._valid_object(value):
            raise AttributeError
        self._data[key] = deepcopy(value)
        self._do_auto_commit()

    def __delattr__(self, key):
        del self._data[key]

    def __get_obj(self, full_path):
        """
        Returns the object which is under the given path
        """
        if isinstance(full_path, (tuple, list)):
            steps = full_path
        else:
            steps = full_path.split(".")
        path = []
        obj = self._data
        if not full_path:
            return obj
        for step in steps:
            path.append(step)
            try:
                obj = obj[step]
            except KeyError:
                raise KeyError(".".join(path))
        return obj

    def __setitem__(self, name, value):
        path, _, key = name.rpartition(".")
        if self._valid_object(value):
            dictionary = self.__get_obj(path)
            dictionary[key] = deepcopy(value)
            self._do_auto_commit()
        else:
            raise AttributeError

    def __getitem__(self, key):
        obj = self.__get_obj(key)
        if obj is self._data:
            raise KeyError
        return deepcopy(obj)

    def __delitem__(self, name):
        if isinstance(name, (tuple, list)):
            path = name[:-1]
            key = name[-1]
        else:
            path, _, key = name.rpartition(".")
        obj = self.__get_obj(path)
        del obj[key]

    def __contains__(self, key):
        return key in self._data
