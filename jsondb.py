#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
import json
import sys
"""
TODO:
 * make sure inserted values are JSON serialiseable
 * document
 * make backup file when saving
 * don't eat ValueError+IOError in constructor
 * add transaction contexts
"""


class JSONDb(object):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.__flush()

    def __flush(self):
        with open(self.__dict__['__path'], 'wb') as f:
            output = json.dumps(self.__dict__['__data'])
            f.write(output.encode('utf-8'))

    def __init__(self, path, default_to_none=False):
        try:
            data = json.loads(open(path, 'rb').read().decode('utf-8'))
        except ValueError:
            data = {}
        except IOError:
            data = {}
        self.__dict__['__data'] = data
        self.__dict__['__path'] = path
        self.__dict__['__default_to_none'] = default_to_none

    def __getattr__(self, key):
        print(key)
        if key.startswith('_JSONDb__'):
            raise AttributeError
        if key in self.__dict__['__data']:
            return self.__dict__['__data'][key]
        if not self.__dict__['__default_to_none']:
            raise KeyError(key)
        return None

    @staticmethod
    def __valid_object(obj):
        if obj is None:
            return True
        elif isinstance(obj, (int, float, str)):
            return True
        if isinstance(obj, dict):
            return all(
                self.__valid_object(k) and self.__valid_object(v)
                for k, v in obj
                )
        elif isinstance(obj, (list, tuple)):
            return all(self.__valid_object(o) for o in obj)
        elif sys.version_info < (3, ):
            return isinstance(obj, (long, unicode))
        else:
            return False

    def __setattr__(self, key, value):
        if not self.__valid_object(value):
            raise AttributeError
        if key.startswith(' '):
            raise AttributeError
        self.__dict__['__data'][key] = value

    def __delattr__(self, key):
        del self.__dict__['__data'][key]

    __getitem__ = __getattr__
    __setitem__ = __setattr__


with JSONDb('jsondb.json') as db:
    db.password = 'hello'
    db.thing = True
    db.gone = None
    del db.gone
    db.nothing = None
    db['item1'] = 1
    db['bad.name'] = 2
