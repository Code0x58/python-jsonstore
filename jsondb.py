#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
import json
import sys


class JSONDb(object):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._flush()

    def __flush(self):
        with open(self._path, 'wb') as f:
            f.write(bytes(json.dumps(self.__dict__), 'UTF-8'))

    def __init__(self, path=('%s.db' % sys.argv[0]), default_to_none=True):
        try:
            data = json.loads(open(path, 'rb').read().decode('utf-8'))
        except ValueError:
            data = {}
        except IOError:
            data = {}
        self.data = data
        self.path = path
        self.default_to_none = default_to_none

    def __getattr__(self, key):
        print(key)
        if key.startswith('_JSONDB__'):
            raise AttributeError
        if key in self.__data:
            return self.__data[key]
        if not self._default_to_none:
            raise KeyError(key)
        return None

    def __setattr__(self, key, value):
        if key.startswith(' '):
            raise AttributeError
        self.__data[key] = value

    __getitem__ = __getattr__
    __setitem__ = __setattr__

db = JSONDb()
db.ok = 1

with JSONDb() as database:
    database.password = 'hello'
