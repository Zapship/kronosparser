# wordsToNum.py
# Copyright 2006, Paul McGuire
#
# Sample parser grammar to read a number given in words, and return the numeric value.
#
import functools
import operator

import pyparsing

from kronosparser import utils


def make_entity(definitions):
    sorted_keys = sorted(definitions, key=len, reverse=True)
    return utils.caseless_keyword_or(sorted_keys).setParseAction(
        lambda x: definitions[x[0].lower()])


unit_definitions = {
    'zero': 0,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
    'thirteen': 13,
    'fourteen': 14,
    'fifteen': 15,
    'sixteen': 16,
    'seventeen': 17,
    'eighteen': 18,
    'nineteen': 19,
}
units = make_entity(unit_definitions)

tens_definitions = {
    'ten': 10,
    'twenty': 20,
    'thirty': 30,
    'forty': 40,
    'fourty': 40,  # for the spelling-challenged...
    'fifty': 50,
    'sixty': 60,
    'seventy': 70,
    'eighty': 80,
    'ninety': 90,
}
tens = make_entity(tens_definitions)

hundred_definitions = {
    'hundred': 100,
    'hundreds': 100,
}
hundreds = make_entity(hundred_definitions)

major_definitions = {
    'thousand': 10**3,
    'thousands': 10**3,
    'million': 10**6,
    'millions': 10**6,
    'billion': 10**9,
    'billions': 10**9,
    'trillion': 10**12,
    'trillions': 10**12,
    'quadrillion': 10**15,
    'quadrillions': 10**15,
    'quintillion': 10**18,
    'quintillions': 10**18,
}
major = make_entity(major_definitions)


def mul(values):
    return functools.reduce(operator.mul, values)


hundred_part = (pyparsing.Optional(units) + hundreds).setParseAction(mul)

tens_units = pyparsing.MatchFirst([(tens + units).setParseAction(sum), tens, units])
num_part = pyparsing.MatchFirst([pyparsing.Optional(hundred_part) + tens_units,
                                 hundred_part]).setParseAction(sum)

word_number = pyparsing.OneOrMore(
    pyparsing.MatchFirst([num_part + pyparsing.Optional(major),
                          major]).setParseAction(mul)).setParseAction(lambda t: {'int': sum(t)})
word_number.ignore(pyparsing.Literal('-'))
word_number.ignore(pyparsing.Literal(','))
word_number.ignore(pyparsing.CaselessKeyword('and'))
