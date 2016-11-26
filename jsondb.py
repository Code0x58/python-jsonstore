#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
import json
"""
TODO:
 * make sure inserted values are JSON serialiseable
 * document
 * make backup file when saving
 * don't eat ValueError+IOError in constructor
 * avoid double flush when used as context manager
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

    def __del__(self):
        self.__flush()

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

    def __setattr__(self, key, value):
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
    db.other = 1
    del db.other
