#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
import json
import sys
from collections import OrderedDict
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
            output = json.dumps(
                self.__dict__['__data'],
                indent=self.__dict__['__indent'],
                )
            f.write(output.encode('utf-8'))

    def __init__(self, path, indent=None):
        try:
            data = json.loads(
                open(path, 'rb').read().decode('utf-8'),
                object_pairs_hook=OrderedDict,
                )
        except ValueError:
            data = {}
        except IOError:
            data = {}
        self.__dict__['__data'] = data
        self.__dict__['__path'] = path
        self.__dict__['__indent'] = indent

    def __getattr__(self, key):
        if key.startswith('_JSONDb__'):
            raise AttributeError
        if key in self.__dict__['__data']:
            return self.__dict__['__data'][key]
        if not self.__dict__['__default_to_none']:
            raise KeyError(key)
        return None

    @classmethod
    def __valid_object(cls, obj):
        if obj is None:
            return True
        elif isinstance(obj, (int, float, str)):
            return True
        if isinstance(obj, dict):
            return all(
                cls.__valid_object(k) and cls.__valid_object(v)
                for k, v in obj.items()
                )
        elif isinstance(obj, (list, tuple)):
            return all(cls.__valid_object(o) for o in obj)
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

    def __get_obj(self, name):
        steps = name.split('.')
        path = []
        obj = self.__dict__['__data']
        if not name:
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
        if self.__valid_object(value):
            dictionary = self.__get_obj(path)
            dictionary[key] = value
        else:
            raise AttributeError

    def __getitem__(self, key):
        obj = self.__get_obj(key)
        if obj is self:
            raise KeyError
        return obj


with JSONDb('jsondb.json', indent=2) as db:
    db.password = 'hello'
    db.thing = True
    db.gone = None
    del db.gone
    db.nothing = None
    db['item1'] = 1
    db.dict = OrderedDict({'key1': 'a'})
    db.dict['key1']
    db['dict.key2'] = 'b'
    assert db['dict.key2'] == 'b'
