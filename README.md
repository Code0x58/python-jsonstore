# jsonstore
This module provides a class that maps keys and values from a JSON file onto its
attributes.

The goal was to provide a convenient way of loading and saving configuration in
a familiar human readable format. This is a bit more flexible than the
[configparser](https://docs.python.org/3/library/configparser.html) module which
is included with Python.

This works with Python 2.7+ and Python 3.0+

## Example
```python
from jsonstore import JsonStore

# the JSON file is saved when the context manager exits
with JsonStore('config.json', indent=2) as store:
  store.a_string = "something"
  store.a_list = [1, 2, 3]
  store.a_dictionary = {
    'dict-list': [{}],
    'ln(2)': 0.69314718056,
    'for-you': u"💐",
  }

  # you can use […] to set/get/delete almost arbitrary keys
  store['some_key'] = "a value"
  # the key is split on '.'s and works on dictionaries
  del store['a_dictionary.dict-list']
  store['a_dictionary.new_value'] = "old value"

  # deep copies are made when assigning values
  my_list = ['fun']
  store.a_list = my_list
  assert store.a_list is not my_list
  # deep copies are also returned to avoid unsanitary changes being made
  store.a_dictionary['new_value'] = "new value"  # won't update the store!
  assert store.a_dictionary['new_value'] == "old value"
  assert store.a_dictionary is not store.a_dictionary
```
