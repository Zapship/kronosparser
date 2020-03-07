kronosparser
======

Parse any type of time instance from text and translate it into a datetime or a time interval.


Install
-------

In the meantime, while I finish adding this as a `pypi` package, you can install
it by using `pip install` directly from the Github repository, as shown below,

::

    pip install git+https://github.com/zapship/kronosparser.git


Usage
-----

First, you need to import both the grammar that defines the parser (in this case `delta_time`) and the `find_all` helper.

.. code:: python
    from kronosparser import delta_time
    from kronosparser.utils import find_all

Then, you can find all the date or time interval instances within an input string, for example:

::

    >>> from pprint import pprint
    >>> from kronosparser import delta_time
    >>> from kronosparser.utils import find_all
    >>> pprint(find_all(delta_time, 'I need the report now, by tomorrow noon, or next week'))
    [{'end': 21,
      'parsed': {'datetime': '2020-03-07 13:36:22', 'utc': True},
      'start': 18,
      'text': 'now'},
     {'end': 39,
      'parsed': {'datetime': '2020-03-08 12:00:00',
                 'days_delta': 1,
                 'tz_threshold': 11,
                 'utc': False},
      'start': 26,
      'text': 'tomorrow noon'},
     {'end': 53,
      'parsed': {'interval': {'end': '2020-03-15', 'start': '2020-03-09'},
                 'utc': False},
      'start': 44,
      'text': 'next week'}]

Note that the example above has 3 types of identified instances: a datetime. I'll add more details about this soon.


Changelog
=========

v0.0.1 (2020-03-06)
-------------------

* Initial commit with delta_time parser and unit tests.
