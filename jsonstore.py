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


class JsonStore(object):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._flush()

    def _load(self):
        if not os.path.exists(self._path):
            with open(self._path, 'w+b'):
                pass
        with open(self._path, 'r+b') as f:
            raw_data = f.read().decode('utf-8')
        if not raw_data:
            data = OrderedDict()
        else:
            data = json.loads(raw_data, object_pairs_hook=OrderedDict)

        if not isinstance(data, dict):
            raise ValueError("Root element is not an object")
        self.__dict__['_data'] = data

    def _flush(self):
        with open(self._path, 'wb') as f:
            output = json.dumps(
                self._data,
                indent=self._indent,
                )
            f.write(output.encode('utf-8'))

    def __init__(self, path, indent=None):
        self.__dict__.update({
            '_data': None,
            '_path': path,
            '_indent': indent,
        })
        self._load()

    def __getattr__(self, key):
        if key in self._data:
            return deepcopy(self._data[key])
        else:
            raise KeyError(key)

    @classmethod
    def _valid_object(cls, obj, parents=None):
        """
        Determine if the object can be encoded into JSON
        """
        # pylint: disable=unicode-builtin,long-builtin
        if isinstance(obj, (dict, list)):
            if parents is None:
                parents = [obj]
            elif any(o is obj for o in parents):
                raise ValueError("Cycle detected in list/dictionary")
            parents.append(obj)

        if obj is None:
            return True
        if isinstance(obj, (bool, int, float, str)):
            return True
        if isinstance(obj, dict):
            return all(
                cls._valid_object(k, parents) and cls._valid_object(v, parents)
                for k, v in obj.items()
                )
        elif isinstance(obj, (list, tuple)):
            return all(cls._valid_object(o, parents) for o in obj)
        elif sys.version_info < (3, ):
            return isinstance(obj, (long, unicode))
        else:
            return False

    def __setattr__(self, key, value):
        if not self._valid_object(value):
            raise AttributeError
        self._data[key] = deepcopy(value)

    def __delattr__(self, key):
        del self._data[key]

    def __get_obj(self, full_path):
        """
        Returns the object which is under the given path
        """
        steps = full_path.split('.')
        path = []
        obj = self._data
        if not full_path:
            return obj
        for step in steps:
            path.append(step)
            try:
                obj = obj[step]
            except AttributeError:
                raise KeyError('.'.join(path))
        return obj

    def __setitem__(self, name, value):
        path, _, key = name.rpartition('.')
        if self._valid_object(value):
            dictionary = self.__get_obj(path)
            dictionary[key] = deepcopy(value)
        else:
            raise AttributeError

    def __getitem__(self, key):
        obj = self.__get_obj(key)
        if obj is self:
            raise KeyError
        return deepcopy(obj)

    def __delitem__(self, name):
        path, _, key = name.rpartition('.')
        obj = self.__get_obj(path)
        del obj[key]
