kronosparser
======

Parse any type of time instance from text and translate it into a date, datetime, or time interval. This could be for either future dates or past dates, and you can set the timezone if available.


Install
-------

In the meantime, while I finish adding this as a ``pypi`` package, you can install
it by using ``pip install`` directly from the Github repository, as shown below,

::

    pip install git+https://github.com/Zapship/kronosparser.git


Usage
-----

To use it you need to import the parse_dates method. There are 3 parameters you can define, besides the input text for your parsing use case:

* future: which states whether you are parsing a text that is supposed to be in the future or the past (particularly helpful for chatbots that asks users questions frame in the past or the future)
* interval_to_date: useful when you have an interval, but you want to just pick a date (usually the closest date).
* timezone: the timezone you want to use for your specific use case.

.. code:: python

    from kronosparser import parse_dates

Then, you can find all the date or time interval instances within an input string, for example:

::

    >>> from pprint import pprint
    >>> from kronosparser import parse_dates
    >>> pprint(parse_dates('I need the report now, by tomorrow noon, or next week', interval_to_date=False))
    [{'end': 21,
      'parsed': {'datetime': '2020-03-11 14:20:38-07:00'},
      'start': 18,
      'text': 'now'},
     {'end': 39,
      'parsed': {'datetime': '2020-03-12 12:00:00'},
      'start': 26,
      'text': 'tomorrow noon'},
     {'end': 53,
      'parsed': {'interval': {'end': '2020-03-22', 'start': '2020-03-16'}},
      'start': 44,
      'text': 'next week'}]


Note that the example above has 3 types of identified instances: a datetime with timezone, a datetime without timezone, and a time interval.

Other examples:

::

    >>> pprint(parse_dates('I need the report by tomorrow'))
    [{'end': 29, 'parsed': {'date': '2020-03-12'}, 'start': 21, 'text': 'tomorrow'}]


    >>> pprint(parse_dates('I need the report now, by tomorrow noon, or next week', interval_to_date=False))
    {'end': 21,
      'parsed': {'datetime': '2020-03-11 14:22:27-07:00'},
      'start': 18,
      'text': 'now'},
     {'end': 39,
      'parsed': {'datetime': '2020-03-12 12:00:00'},
      'start': 26,
      'text': 'tomorrow noon'},
     {'end': 53,
      'parsed': {'interval': {'end': '2020-03-22', 'start': '2020-03-16'}},
      'start': 44,
      'text': 'next week'}]


    >>>  pprint(parse_dates('friday', future=True))
    [{'end': 6, 'parsed': {'date': '2020-03-13'}, 'start': 0, 'text': 'friday'}]


    >>> pprint(parse_dates('friday', future=False))
    [{'end': 6, 'parsed': {'date': '2020-03-06'}, 'start': 0, 'text': 'friday'}]



Note that if you don't define the ``timezone``, it will use ``US/Pacific`` by default. Also, is no parameters are specified, it will use ``future`` as ``False`` and ``interval_to_date`` as ``True``.


Changelog
=========

v0.0.1 (2020-03-06)
-------------------

* Initial commit with delta_time parser and unit tests.
